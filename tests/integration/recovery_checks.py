"""Committed synthetic recovery across fresh sessions and a postmaster outage.

No HTTP transport, production resources, persistent storage or resend/reset API.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import time


def restart_recovery(query, actor_query, provision_actor, lifecycle, failure_type):
    actor = 'synthetic_worker'
    query(f'CREATE ROLE {actor} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
    provision_actor(actor)
    query(f'GRANT dincharya_reminder_worker TO {actor}')

    def security():
        assert actor_query(actor,'SELECT session_user') == actor, 'Worker identity mismatch'
        actor_query(actor,'SELECT 1','AUTH')
        assert query("SELECT count(*)=0 FROM pg_hba_file_rules WHERE error IS NOT NULL "
                     "OR (type LIKE 'host%' AND auth_method<>'scram-sha-256') "
                     "OR (auth_method='trust' AND type<>'local')") == 't', 'Unsafe authentication rules'
        assert query("SELECT count(*)>0 FROM pg_hba_file_rules WHERE type='local' AND auth_method='trust'") == 't'
        for sql in ('UPDATE public.reminder_deliveries SET status=\'pending\'',
                    'UPDATE reconcile_private.gate SET enabled=true',
                    'SELECT * FROM reconcile_api.inspect_uncertain()',
                    'DELETE FROM reconcile_private.audit'):
            actor_query(actor,sql,'42501')
        assert query('SELECT NOT enabled FROM reconcile_private.gate') == 't'
        assert query('SELECT count(*) FROM reconcile_private.audit') == '0'
        for setting, expected in {'log_statement':'none','log_min_error_statement':'panic',
                'log_duration':'off','log_min_duration_statement':'-1','log_min_duration_sample':'-1',
                'log_transaction_sample_rate':'0','log_parameter_max_length':'0',
                'log_parameter_max_length_on_error':'0'}.items():
            assert query('SHOW '+setting) == expected, 'Logging configuration changed'

    security()
    clock = query("SELECT ((((now() AT TIME ZONE 'Asia/Kolkata')::date+1)+time '12:00') AT TIME ZONE 'Asia/Kolkata')::text")
    # Values below are generated internally from PostgreSQL, never user input.
    def at(seconds=0):
        return f"('{clock}'::timestamptz+interval '{int(seconds)} seconds')"

    def event(offset):
        return int(query("INSERT INTO public.schedule_events(title,start_time,recurrence,event_date) "
            f"VALUES('Synthetic outage',({at(offset)} AT TIME ZONE 'Asia/Kolkata')::time,'once',"
            f"({at(offset)} AT TIME ZONE 'Asia/Kolkata')::date) RETURNING id").splitlines()[0])

    def claim(seconds=0, limit=1):
        return actor_query(actor, f'SELECT delivery_id,event_id,worker_token FROM '
            f'reminder_worker_api.claim_occurrence_reminders({at(seconds)},{limit})')

    def finish(item, outcome, seconds=0, receipt=False):
        delivery, _, token = item.split('|')
        api = 'acknowledge_occurrence_reminder' if receipt else 'finish_occurrence_reminder'
        extra = ',101,90001' if receipt else ''
        return actor_query(actor, f"SELECT reminder_worker_api.{api}({int(delivery)},'{token}',"
                           f"'{outcome}',{at(seconds)}{extra})")

    def ledger():
        return json.loads(query("SELECT coalesce(jsonb_agg(to_jsonb(d) ORDER BY id),'[]') "
                                'FROM public.reminder_deliveries d'))

    # Distinct due times make ordering deterministic; each call is a new process.
    sent_event, unknown_event, orphan_event, retry_event = [event(n) for n in (-4,-3,-2,-1)]
    sent, unknown, orphan, retry = (claim() for _ in range(4))
    assert [int(row.split('|')[1]) for row in (sent,unknown,orphan,retry)] == [
        sent_event,unknown_event,orphan_event,retry_event]
    assert finish(sent,'sent',receipt=True) == 't'
    assert finish(unknown,'uncertain') == 't'
    # Orphan models worker exit/lost acceptance acknowledgement, not proof of send.
    assert finish(retry,'not_accepted') == 't'
    assert claim(29) == '', 'Backoff ignored across worker reconnect'

    # Pre-materialized edge and replan work must survive the database outage.
    edge, outside = event(-21600),event(-21601)
    replan = event(600)
    query(f'SELECT public.refresh_occurrence_reminders({at()})')
    replan_id = query(f'SELECT id FROM public.reminder_deliveries WHERE event_id={replan}')
    query(f'UPDATE public.schedule_events SET enabled=false WHERE id={replan}')
    query(f'SELECT public.refresh_occurrence_reminders({at()})')
    assert query(f'SELECT status FROM public.reminder_deliveries WHERE id={replan_id}') == 'cancelled'
    committed = ledger()
    postmaster = query('SELECT pg_postmaster_start_time()')

    # A claim inside an uncommitted transaction must be rolled back by the crash.
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(actor_query,actor,"SET application_name='synthetic_uncommitted_claim'; BEGIN; "
            f'SELECT * FROM reminder_worker_api.claim_occurrence_reminders({at()},1); '
            'SELECT pg_sleep(30); COMMIT;')
        deadline = time.monotonic()+10
        while time.monotonic()<deadline:
            if query("SELECT count(*) FROM pg_stat_activity WHERE application_name='synthetic_uncommitted_claim' "
                     "AND wait_event='PgSleep'") == '1':
                break
            time.sleep(0.05)
        else:
            raise AssertionError('Uncommitted claim was not observed')
        lifecycle('stop')
        try:
            pending.result()
        except failure_type:
            pass
        else:
            raise AssertionError('Interrupted uncommitted transaction unexpectedly succeeded')
    try:
        actor_query(actor,'SELECT 1')
    except failure_type:
        pass
    else:
        raise AssertionError('Database did not become unavailable')
    lifecycle('start')
    assert query('SELECT pg_postmaster_start_time()') != postmaster, 'Postmaster did not restart'
    assert ledger() == committed, 'Crash recovery changed committed ledger or retained uncommitted claim'
    security()
    print('PASS postmaster outage/crash rollback, committed ledger durability, fresh SCRAM sessions, '
          'local-only trust and preserved privilege/logging boundaries',flush=True)

    # Recovery at the same clock includes the edge, excludes outside and preserves
    # the orphan lease until expiry. No duplicate claim from the rolled-back work.
    recovered = claim()
    assert int(recovered.split('|')[1]) == edge, 'Restart recovery lost lookback edge'
    assert query(f'SELECT count(*) FROM public.reminder_deliveries WHERE event_id={outside}') == '0'
    assert finish(recovered,'sent',receipt=False) == 't'
    assert claim() == '', 'Restart duplicated committed sent/uncertain or active claims'
    retry_claim = claim(30)
    assert int(retry_claim.split('|')[1]) == retry_event, 'Safe rejection retry did not resume at backoff boundary'
    assert finish(retry_claim,'sent',30) == 't'
    assert finish(retry,'sent',30) == 'f', 'Old retry token acknowledged a new attempt'
    assert claim(120) == '', 'Expired orphan lease automatically replayed'
    assert finish(orphan,'sent',120,receipt=True) == 'f', 'Expired pre-outage token acknowledged'
    terminal = ledger()
    by_event = {r['event_id']:r for r in terminal}
    assert by_event[orphan_event]['status'] == 'uncertain' and by_event[orphan_event]['attempts'] == 1
    assert by_event[orphan_event]['worker_token'] is None and by_event[orphan_event]['lease_until'] is None
    assert by_event[unknown_event] == next(r for r in committed if r['event_id']==unknown_event)
    assert by_event[sent_event] == next(r for r in committed if r['event_id']==sent_event)

    # Re-enable at a new due time on the same India occurrence date.
    query(f"UPDATE public.schedule_events SET enabled=true,start_time=({at(1200)} AT TIME ZONE 'Asia/Kolkata')::time,"
          f"event_date=({at(1200)} AT TIME ZONE 'Asia/Kolkata')::date WHERE id={replan}")
    assert claim(600) == '', 'Replanned work claimed at old time'
    planned = claim(1200)
    assert planned.split('|')[0] == replan_id, 'Replan changed occurrence identity'
    assert finish(planned,'sent',1200) == 't'
    assert claim(1200) == '', 'Replan generated duplicate delivery'
    query(f'SELECT public.refresh_occurrence_reminders({at(86400)})')
    assert claim(86400) == '', 'Long outage replayed terminal history'
    assert query('SELECT count(*) FROM reconcile_private.audit') == '0'
    print('PASS post-outage lookback/backoff boundaries, stale tokens, lease quarantine, immutable sent/uncertain '
          'history, stable cancellation/replan identity and duplicate suppression',flush=True)
