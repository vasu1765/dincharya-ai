"""Multi-session managed-boundary assertions with an injected disposable SQL client."""
from concurrent.futures import ThreadPoolExecutor
import time


def concurrent_legacy_boundary(query):
    """Commit synthetic rows; caller must use a fresh disposable application DB."""
    event = int(query("INSERT INTO public.schedule_events(title,start_time,end_time,recurrence,timezone) "
                      "VALUES('Synthetic concurrent transition','13:00','13:15','daily','Asia/Kolkata') RETURNING id").splitlines()[0])
    request = int(query(
        "INSERT INTO public.schedule_change_requests(action,event_id,requested_by,proposed_data) "
        "SELECT 'remove',id,101,jsonb_build_object('original',jsonb_build_object("
        "'title',title,'start_time',start_time,'end_time',end_time,'recurrence',recurrence,"
        "'weekdays',weekdays,'event_date',event_date,'timezone',timezone,'enabled',enabled,'notes',notes)) "
        f"FROM public.schedule_events WHERE id={event} RETURNING id").splitlines()[0])
    proposal = int(query(
        "SELECT public.propose_gregorian_change('update','series',"
        f"{event},NULL,jsonb_build_object('title','Synthetic concurrent transition','start_time','13:00',"
        "'end_time','13:15','timezone','Asia/Kolkata','recurrence_rule',jsonb_build_object("
        "'calendar_system','gregorian','frequency','daily','interval_count',1,"
        "'start_date',(now() AT TIME ZONE 'Asia/Kolkata')::date)),101)"))
    transaction = (
        f"BEGIN; SELECT success::text FROM public.decide_gregorian_change({proposal},101,'approve'); "
        "SELECT pg_sleep(5); COMMIT;")
    decision = f"SELECT success::text FROM public.process_schedule_decision({request},101,'approve',true)"
    with ThreadPoolExecutor(max_workers=4) as pool:
        conversion = pool.submit(query, transaction)
        deadline = time.monotonic() + 15
        while query('SELECT pg_try_advisory_xact_lock(20261112,1)') != 'f':
            if conversion.done() or time.monotonic() >= deadline:
                raise AssertionError('Conversion lock was not observed')
            time.sleep(0.05)
        decisions = [pool.submit(query, decision) for _ in range(2)]
        submission = pool.submit(query,
            f"DO $$ BEGIN PERFORM public.create_schedule_change_proposal('remove',{event},101); "
            "RAISE EXCEPTION 'Concurrent legacy submission accepted managed event'; "
            "EXCEPTION WHEN invalid_parameter_value THEN NULL; END $$")
        blocked = False
        while not conversion.done() and time.monotonic() < deadline:
            waiters = int(query("SELECT count(*) FROM pg_locks WHERE locktype='advisory' "
                                "AND classid=20261112 AND objid=1 AND NOT granted"))
            if waiters >= 2:
                blocked = True
                break
            time.sleep(0.05)
        assert blocked, 'Concurrent legacy decisions did not wait on conversion'
        result = conversion.result()
        assert 'true' in result.splitlines() and 'false' not in result.splitlines(), 'Conversion failed'
        assert [future.result() for future in decisions] == ['false', 'false'], 'Concurrent policy bypass'
        assert submission.result() == 'DO', 'Concurrent legacy submission not blocked'
    assert query(f"SELECT status FROM public.schedule_change_requests WHERE id={request}") == 'pending'
    assert query(f"SELECT enabled FROM public.schedule_events WHERE id={event}") == 't'
    assert query(f"SELECT count(*) FROM public.schedule_change_requests WHERE event_id={event}") == '2'
    print('PASS concurrent conversion, two blocked legacy decisions and blocked fresh legacy submission', flush=True)
