"""New multi-session API/receipt assertions; injected disposable SQL client only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier


def race(query, statements):
    barrier = Barrier(len(statements))
    def run(statement):
        barrier.wait(timeout=10)
        return query(statement)
    with ThreadPoolExecutor(max_workers=len(statements)) as pool:
        return list(pool.map(run, statements))


def adversarial_decisions(query):
    def proposal(title, slot, *, event=None):
        action = 'add' if event is None else 'update'
        target = 'NULL' if event is None else str(event)
        return int(query(
            f"SELECT public.propose_gregorian_change('{action}','series',{target},NULL,"
            f"jsonb_build_object('title','{title}','start_time','{slot}:00','end_time','{slot}:15',"
            "'timezone','Asia/Kolkata','recurrence_rule',jsonb_build_object('calendar_system','gregorian',"
            "'frequency','once','interval_count',1,'start_date',"
            "(now() AT TIME ZONE 'Asia/Kolkata')::date+1)),101)"))
    def decide(request, owner=101, action='approve'):
        return f"SELECT success::text FROM public.decide_gregorian_change({request},{owner},'{action}')"
    first, second = proposal('Synthetic conflict A', '10'), proposal('Synthetic conflict B', '10')
    assert sorted(race(query, [decide(first), decide(second)])) == ['false', 'true'], 'Concurrent conflict bypass'
    assert query(f"SELECT string_agg(status,',' ORDER BY status) FROM public.schedule_change_requests WHERE id IN ({first},{second})") == 'approved,pending'

    request = proposal('Synthetic stale base', '12')
    assert query(decide(request)) == 'true'
    event = int(query(f'SELECT event_id FROM public.schedule_change_requests WHERE id={request}'))
    first, second = proposal('Synthetic stale A', '12', event=event), proposal('Synthetic stale B', '12', event=event)
    assert sorted(race(query, [decide(first), decide(second)])) == ['false', 'true'], 'Concurrent stale snapshot accepted'
    assert query(f"SELECT string_agg(status,',' ORDER BY status) FROM public.schedule_change_requests WHERE id IN ({first},{second})") == 'approved,pending'

    request = proposal('Synthetic approve reject race', '14')
    assert sorted(race(query, [decide(request), decide(request, action='reject')])) == ['false', 'true'], 'Decision replay race accepted twice'
    state = query(f'SELECT status,event_id IS NULL FROM public.schedule_change_requests WHERE id={request}')
    assert state in ('approved|f', 'rejected|t'), 'Decision/event identity mismatch'

    request = proposal('Synthetic authorization race', '16')
    assert race(query, [decide(request, owner=999), decide(request)]) == ['false', 'true'], 'Concurrent authorization bypass'
    assert query(f"SELECT status FROM public.schedule_change_requests WHERE id={request}") == 'approved'
    print('PASS conflict, stale-update, approve/reject and unauthorized-owner multi-session races', flush=True)


def concurrent_receipt(query):
    query("INSERT INTO public.schedule_events(title,start_time,recurrence,event_date) "
          "VALUES('Synthetic receipt race',(date_trunc('minute',now()) AT TIME ZONE 'Asia/Kolkata')::time,"
          "'once',(now() AT TIME ZONE 'Asia/Kolkata')::date)")
    delivery, token = query('SELECT delivery_id,worker_token FROM public.claim_occurrence_reminders(now(),1)').split('|')
    delivery = int(delivery)
    statements = [f"SELECT public.acknowledge_occurrence_reminder({delivery},'{token}'::uuid,'sent',now(),101,{message})"
                  for message in (17, 18)]
    assert sorted(race(query, statements)) == ['f', 't'], 'Concurrent receipt acknowledgement accepted twice'
    state = query(f"SELECT status,attempts,telegram_chat_id,telegram_message_id,worker_token IS NULL "
                  f"FROM public.reminder_deliveries WHERE id={delivery}")
    assert state in ('sent|1|101|17|t', 'sent|1|101|18|t'), 'Receipt race overwrote status/identity'
    assert query('SELECT count(*) FROM public.claim_occurrence_reminders(now(),1)') == '0', 'Sent receipt reclaimed'
    print('PASS competing receipt acknowledgements, immutable winning receipt and no duplicate claim', flush=True)
