"""Invented evidence and actual non-superuser DB sessions; no Telegram dependency."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
import json
import time

ACTORS = ('synthetic_operator_a', 'synthetic_operator_b', 'synthetic_worker',
          'synthetic_outsider', 'synthetic_dual')
REASON = 'Synthetic owner-attested positive delivery evidence'


def run_reconciliation(query, actor_query, provision_actor, *, concurrent=False, review_only=False):
    if review_only:
        for setting, value in {'log_statement':'none', 'log_min_error_statement':'panic',
                'log_min_duration_statement':'-1', 'log_min_duration_sample':'-1', 'log_duration':'off',
                'log_transaction_sample_rate':'0', 'log_parameter_max_length':'0',
                'log_parameter_max_length_on_error':'0'}.items():
            assert query('SHOW '+setting) == value, 'Unsafe synthetic server logging setting'
    for actor in ACTORS:
        query(f'CREATE ROLE {actor} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
        provision_actor(actor)
        assert actor_query(actor,'SELECT session_user') == actor, 'Database login identity mismatch'
    actor_query('synthetic_operator_a','SELECT 1','AUTH')
    query('GRANT dincharya_reconcile_operator TO synthetic_operator_a,synthetic_operator_b,synthetic_dual; '
          'GRANT dincharya_reminder_worker TO synthetic_worker,synthetic_dual')
    query("INSERT INTO reconcile_private.operators(role_oid,role_name,destination,enabled) "
          "SELECT oid,rolname,101,true FROM pg_roles WHERE rolname IN "
          "('synthetic_operator_a','synthetic_operator_b','synthetic_dual')")

    def fixture(*, actor='synthetic_operator_a', verified=True, approved=True, expired=False,
                proof_chat=101, message=None, state='uncertain', leased=False, route_chat=101,
                expiry_seconds=900):
        action, evidence, authorization = str(uuid4()), str(uuid4()), str(uuid4())
        message = message or int(uuid4().int % 1000000000 + 1)
        event = int(query("INSERT INTO public.schedule_events(title,start_time,recurrence,event_date) "
            "VALUES('Synthetic reconciliation',((now()-interval '5 minutes') AT TIME ZONE 'Asia/Kolkata')::time,"
            "'once',((now()-interval '5 minutes') AT TIME ZONE 'Asia/Kolkata')::date) RETURNING id").splitlines()[0])
        token = 'gen_random_uuid()' if leased else 'NULL'
        lease = "now()+interval '1 minute'" if leased else 'NULL'
        delivery = int(query("INSERT INTO public.reminder_deliveries(event_id,occurrence_date,status,managed_by,"
            "due_at,payload,attempts,retry_at,claimed_at,worker_token,lease_until,error_message) "
            f"VALUES({event},((now()-interval '5 minutes') AT TIME ZONE 'Asia/Kolkata')::date,'{state}','m2e',"
            f"now()-interval '5 minutes','{{}}',2,now()-interval '5 minutes',now()-interval '2 minutes',"
            f"{token},{lease},'Synthetic unresolved outcome') RETURNING id").splitlines()[0])
        version = query("SELECT encode(sha256(convert_to(to_jsonb(d)::text,'UTF8')),'hex') "
                        f'FROM public.reminder_deliveries d WHERE id={delivery}')
        if route_chat is not None:
            query(f'INSERT INTO reconcile_private.delivery_destinations(delivery_id,chat_id) VALUES({delivery},{route_chat})')
        query("INSERT INTO reconcile_private.evidence(evidence_ref,delivery_id,chat_id,message_id,digest,delivered_at,verified) "
              f"VALUES('{evidence}',{delivery},{proof_chat},{message},repeat('a',64),now()-interval '1 minute',{str(verified).lower()})")
        expiry = "now()-interval '1 second'" if expired else f"now()+interval '{int(expiry_seconds)} seconds'"
        query("INSERT INTO reconcile_private.authorizations(authorization_ref,action_id,operator_oid,delivery_id,"
              "evidence_ref,observation_version,reason,approved,expires_at) "
              f"VALUES('{authorization}','{action}','{actor}'::regrole::oid,{delivery},'{evidence}',"
              f"'{version}','{REASON}',{str(approved).lower()},{expiry})")
        return dict(action=action, delivery=delivery, evidence=evidence, authorization=authorization,
                    version=version, chat=101, message=message, reason=REASON, confirmed='true')

    def call(values, actor='synthetic_operator_a', prefix=''):
        return actor_query(actor, prefix + statement(values)).splitlines()[-1]

    def statement(values):
        return "SELECT * FROM reconcile_api.record_confirmed_delivered(" + (
            "'{action}',{delivery},'{version}',{chat},{message},'{evidence}','{reason}','{authorization}',{confirmed})"
        ).format(**values)

    def projection(delivery):
        return query(f'SELECT to_jsonb(d) FROM public.reminder_deliveries d WHERE id={delivery}')

    def rejects(values, code, *, actor='synthetic_operator_a', prefix=''):
        before = projection(values['delivery'])
        count = query('SELECT count(*) FROM reconcile_private.audit')
        assert call(values, actor, prefix) == 'f|f|' + code, 'Unexpected reconciliation rejection category'
        assert projection(values['delivery']) == before, 'Rejected reconciliation changed delivery'
        assert query('SELECT count(*) FROM reconcile_private.audit') == count, 'Rejected reconciliation appended audit'

    if review_only:
        query('UPDATE reconcile_private.gate SET enabled=true')
        values = fixture(expiry_seconds=6)
        before = projection(values['delivery'])

        def await_activity(name, wait_type):
            deadline = time.monotonic()+4
            while time.monotonic()<deadline:
                if query("SELECT count(*) FROM pg_stat_activity WHERE application_name="
                         f"'{name}' AND wait_event_type='{wait_type}'") == '1':
                    return
                time.sleep(0.05)
            raise AssertionError('Expected synthetic lock wait was not observed')

        with ThreadPoolExecutor(max_workers=2) as pool:
            holder = pool.submit(query, "SET application_name='synthetic_expiry_holder'; BEGIN; "
                f"SELECT id FROM public.reminder_deliveries WHERE id={values['delivery']} FOR UPDATE; "
                'SELECT pg_sleep(8); COMMIT;')
            await_activity('synthetic_expiry_holder','Timeout')
            decision = pool.submit(call,values,'synthetic_operator_a',
                                   "SET application_name='synthetic_expiry_operator'; ")
            await_activity('synthetic_expiry_operator','Lock')
            assert query("SELECT expires_at>clock_timestamp() FROM reconcile_private.authorizations "
                         f"WHERE authorization_ref='{values['authorization']}'") == 't', 'Permit expired before lock wait'
            holder.result()
            assert decision.result() == 'f|f|authorization_invalid', 'Expired waiting permit was accepted'
        assert projection(values['delivery']) == before, 'Expired permit changed delivery'
        assert query('SELECT count(*) FROM reconcile_private.audit') == '0', 'Expired permit appended audit'
        query('UPDATE reconcile_private.gate SET enabled=false')
        print('PASS SCRAM login and wrong-password rejection; secret-safe server logging; '
              'permit expiry during row-lock wait rejected without delivery/audit writes; gate disabled', flush=True)
        return

    # Gate starts off and cannot be changed by either caller role.
    initial = fixture()
    assert call(initial) == 'f|f|disabled', 'Synthetic gate was not disabled by default'
    actor_query('synthetic_operator_a', 'SELECT * FROM reconcile_api.inspect_uncertain()', '42501')
    actor_query('synthetic_operator_a', 'UPDATE reconcile_private.gate SET enabled=true', '42501')
    actor_query('synthetic_worker', statement(initial), '42501')
    actor_query('synthetic_outsider', statement(initial), '42501')
    query('UPDATE reconcile_private.gate SET enabled=true')
    actor_query('synthetic_operator_a', 'SELECT * FROM reconcile_api.inspect_uncertain(-1,1)', '22023')
    assert actor_query('synthetic_operator_a', 'SELECT count(*) FROM reconcile_api.inspect_uncertain(0,1)') == '1'
    assert actor_query('synthetic_operator_a', "SET TIME ZONE 'Asia/Kolkata'; SELECT observation_version FROM reconcile_api.inspect_uncertain() "
                       f"WHERE delivery_id={initial['delivery']}").splitlines()[-1] == initial['version'], 'Observation timezone mismatch'
    actor_query('synthetic_operator_a', 'SET ROLE dincharya_reconcile_executor', '42501')
    actor_query('synthetic_worker', 'SET ROLE dincharya_worker_executor', '42501')
    actor_query('synthetic_operator_a', 'SELECT * FROM reminder_worker_api.claim_occurrence_reminders(now(),1)', '42501')
    actor_query('synthetic_worker', 'SET ROLE dincharya_reconcile_operator', '42501')
    actor_query('synthetic_operator_b', 'SET SESSION AUTHORIZATION synthetic_operator_a', '42501')
    rejects(initial, 'authorization_invalid', actor='synthetic_operator_b',
            prefix="SET request.operator_id='synthetic_operator_a'; ")
    rejects(initial, 'not_authorized', actor='synthetic_dual')
    for actor in ('synthetic_worker', 'synthetic_operator_a'):
        for sql in ('UPDATE public.reminder_deliveries SET status=\'pending\'',
                    'INSERT INTO reconcile_private.audit DEFAULT VALUES',
                    'UPDATE reconcile_private.audit SET reason=\'forged\'',
                    'DELETE FROM reconcile_private.audit', 'TRUNCATE reconcile_private.audit',
                    'SELECT * FROM reconcile_private.evidence',
                    'SELECT payload,telegram_chat_id FROM public.reminder_deliveries',
                    'INSERT INTO reconcile_private.delivery_destinations DEFAULT VALUES',
                    'UPDATE reconcile_private.authorizations SET approved=true'):
            actor_query(actor, sql, '42501')
    print('PASS authenticated login identity, default-off gate, spoof/role escalation and direct-write privilege boundaries', flush=True)

    for override in ({'confirmed': 'false'}, {'chat': 999}, {'message': 0}, {'reason': ''}):
        rejects(dict(initial, **override), 'invalid_request')
    rejects(dict(initial, evidence=str(uuid4())), 'authorization_invalid')
    rejects(dict(initial, authorization=str(uuid4())), 'authorization_invalid')
    rejects(dict(initial, reason='Different unapproved reason'), 'authorization_invalid')
    rejects(fixture(approved=False), 'authorization_invalid')
    rejects(fixture(expired=True), 'authorization_invalid')
    rejects(fixture(verified=False), 'evidence_invalid')
    rejects(fixture(proof_chat=999), 'evidence_invalid')
    rejects(fixture(route_chat=999), 'destination_invalid')
    rejects(fixture(route_chat=None), 'destination_invalid')
    rejects(fixture(state='sent'), 'unavailable')
    rejects(fixture(leased=True), 'unavailable')
    rejects(fixture(state='sending',leased=True), 'unavailable')
    stale = fixture()
    query(f"UPDATE public.reminder_deliveries SET error_message='Synthetic intervening change' WHERE id={stale['delivery']}")
    rejects(stale, 'stale_observation')
    print('PASS evidence/destination/permit/confirmation, stale, leased and already-resolved rejection without writes', flush=True)

    # Fail AFTER INSERT to prove even an already-inserted audit row and prior
    # ledger UPDATE roll back together. Same action remains available afterward.
    failed = fixture()
    before = projection(failed['delivery'])
    query("CREATE FUNCTION reconcile_private.synthetic_fault() RETURNS trigger LANGUAGE plpgsql AS $$ "
          "BEGIN RAISE EXCEPTION 'Synthetic audit fault'; END $$; "
          "CREATE TRIGGER synthetic_fault AFTER INSERT ON reconcile_private.audit "
          "FOR EACH ROW EXECUTE FUNCTION reconcile_private.synthetic_fault()")
    rejects(failed, 'storage_failed')
    assert projection(failed['delivery']) == before
    query('DROP TRIGGER synthetic_fault ON reconcile_private.audit; DROP FUNCTION reconcile_private.synthetic_fault()')
    assert call(failed, prefix='SET ROLE dincharya_reconcile_operator; ') == 't|f|recorded', 'Retry of rolled-back action failed'
    assert call(failed) == 't|t|replayed', 'Exact action replay was not idempotent'
    rejects(dict(failed, message=failed['message']+1), 'action_mismatch')
    duplicate_receipt = fixture(message=failed['message'])
    rejects(duplicate_receipt, 'identity_conflict')
    assert query(f"SELECT status,attempts,worker_token IS NULL,lease_until IS NULL FROM public.reminder_deliveries WHERE id={failed['delivery']}") == 'sent|2|t|t'
    assert query(f"SELECT operator_name,action,before_version<>after_version FROM reconcile_private.audit WHERE action_id='{failed['action']}'") == 'synthetic_operator_a|record_confirmed_delivered|t'
    old_fields, new_fields = json.loads(before), json.loads(projection(failed['delivery']))
    for key in ('status','sent_at','telegram_chat_id','telegram_message_id'):
        old_fields.pop(key); new_fields.pop(key)
    assert old_fields == new_fields, 'Resolution changed historical payload/attempt/lease fields'
    rolled_back = fixture()
    before_rollback = projection(rolled_back['delivery'])
    result = actor_query('synthetic_operator_a','BEGIN; '+statement(rolled_back)+'; ROLLBACK;')
    assert 't|f|recorded' in result.splitlines()
    assert projection(rolled_back['delivery']) == before_rollback, 'Caller rollback retained state change'
    assert query(f"SELECT count(*) FROM reconcile_private.audit WHERE action_id='{rolled_back['action']}'") == '0'
    assert call(rolled_back) == 't|f|recorded', 'Rolled-back action was consumed'
    for sql in ("UPDATE reconcile_private.audit SET reason='forged'", 'DELETE FROM reconcile_private.audit',
                'TRUNCATE reconcile_private.audit'):
        actor_query('synthetic_test', sql, '55000')
    print('PASS atomic audit/state rollback, exact replay, mismatched replay, receipt uniqueness and preserved attempts/history', flush=True)

    if concurrent:
        def pair(values, actors):
            barrier = Barrier(2)
            def run(item):
                actor, command = item
                barrier.wait(timeout=10)
                return call(command, actor)
            with ThreadPoolExecutor(max_workers=2) as pool:
                return list(pool.map(run, zip(actors, values)))
        first = fixture()
        second = dict(first, action=str(uuid4()), authorization=str(uuid4()))
        query("INSERT INTO reconcile_private.authorizations(authorization_ref,action_id,operator_oid,delivery_id,"
              "evidence_ref,observation_version,reason,approved,expires_at) "
              f"VALUES('{second['authorization']}','{second['action']}','synthetic_operator_b'::regrole::oid,"
              f"{second['delivery']},'{second['evidence']}','{second['version']}','{REASON}',true,now()+interval '15 minutes')")
        assert sorted(pair([first, second], ['synthetic_operator_a', 'synthetic_operator_b'])) == ['f|f|unavailable', 't|f|recorded']
        assert query(f"SELECT count(*) FROM reconcile_private.audit WHERE delivery_id={first['delivery']}") == '1'
        same = fixture()
        assert sorted(pair([same, same], ['synthetic_operator_a']*2)) == ['t|f|recorded', 't|t|replayed']
        assert query(f"SELECT count(*) FROM reconcile_private.audit WHERE delivery_id={same['delivery']}") == '1'
        print('PASS concurrent distinct decisions and concurrent identical action replay; one transition and audit each', flush=True)

    # Normal worker uses only its scoped wrappers; it cannot resolve uncertainty.
    query("INSERT INTO public.schedule_events(title,start_time,recurrence,event_date) VALUES("
          "'Synthetic restricted worker',(date_trunc('minute',now()) AT TIME ZONE 'Asia/Kolkata')::time,"
          "'once',(now() AT TIME ZONE 'Asia/Kolkata')::date)")
    claim = actor_query('synthetic_worker', 'SELECT delivery_id,worker_token FROM reminder_worker_api.claim_occurrence_reminders(now(),1)')
    delivery, token = claim.split('|')
    assert actor_query('synthetic_worker', f"SELECT reminder_worker_api.acknowledge_occurrence_reminder({int(delivery)},'{token}','sent',now(),101,900000000000)") == 't'
    assert actor_query('synthetic_worker', f"SELECT reminder_worker_api.acknowledge_occurrence_reminder({int(delivery)},'{token}','sent',now(),101,900000000000)") == 'f'
    assert actor_query('synthetic_worker', 'SELECT count(*) FROM reminder_worker_api.claim_occurrence_reminders(now(),1)') == '0'
    query('UPDATE reconcile_private.gate SET enabled=false')
    assert call(initial) == 'f|f|disabled'
    print('PASS restricted worker claim/normal acknowledgement/replay and final synthetic gate disabled', flush=True)
