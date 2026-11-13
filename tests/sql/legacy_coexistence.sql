BEGIN;
SET LOCAL plpgsql.check_asserts=on;
DO $$
DECLARE legacy_request bigint; legacy_event bigint; managed_request bigint; managed_event bigint;
 change_request bigint; ok boolean; before_state jsonb; data jsonb; claim record;
 test_day date := (now() AT TIME ZONE 'Asia/Kolkata')::date;
BEGIN
 -- A legacy add still uses its old envelope and does not acquire a v2 rule.
 INSERT INTO public.schedule_change_requests(action,requested_by,proposed_data)
 VALUES('add',101,jsonb_build_object('title','Synthetic legacy coexistence',
   'start_time','08:00','end_time','08:15','timezone','Asia/Kolkata','recurrence','daily'))
 RETURNING id INTO legacy_request;
 SELECT success INTO ok FROM public.dispatch_schedule_decision(legacy_request,999,'approve');
 ASSERT ok IS FALSE,'Unauthorized legacy decision accepted';
 ASSERT NOT EXISTS(SELECT FROM public.schedule_events),'Unauthorized legacy decision mutated events';
 SELECT success INTO ok FROM public.dispatch_schedule_decision(legacy_request,101,'approve');
 ASSERT ok IS TRUE,'Legacy add no longer works';
 SELECT event_id INTO legacy_event FROM public.schedule_change_requests WHERE id=legacy_request;
 ASSERT legacy_event IS NOT NULL,'Legacy event identity missing';
 ASSERT NOT EXISTS(SELECT FROM public.recurrence_rules WHERE event_id=legacy_event
   AND rule_options->>'managed_by'='m2d'), 'Legacy add became managed';
 SELECT success INTO ok FROM public.dispatch_schedule_decision(legacy_request,101,'approve');
 ASSERT ok IS FALSE,'Legacy approval replay accepted';

 data:=jsonb_build_object('title','Synthetic managed coexistence','start_time','09:00',
  'end_time','09:15','timezone','Asia/Kolkata','recurrence_rule',jsonb_build_object(
    'calendar_system','gregorian','frequency','daily','interval_count',1,'start_date',test_day));
 managed_request:=public.propose_gregorian_change('add','series',NULL,NULL,data,101);
 SELECT success INTO ok FROM public.dispatch_schedule_decision(managed_request,101,'approve');
 ASSERT ok IS TRUE,'Managed add failed beside legacy event';
 SELECT event_id INTO managed_event FROM public.schedule_change_requests WHERE id=managed_request;
 ASSERT (SELECT count(*) FROM public.generate_event_occurrences(test_day,test_day))=2,
   'Legacy/managed occurrence coexistence failed';
 before_state:=public.gregorian_snapshot(managed_event);

 -- Legacy decisions retain requester ownership and do not touch managed rows.
 INSERT INTO public.schedule_change_requests(action,event_id,requested_by,proposed_data)
 VALUES('remove',legacy_event,101,jsonb_build_object('original',
   (SELECT jsonb_build_object('title',e.title,'start_time',e.start_time,'end_time',e.end_time,
    'recurrence',e.recurrence,'weekdays',e.weekdays,'event_date',e.event_date,
    'timezone',e.timezone,'enabled',e.enabled,'notes',e.notes)
    FROM public.schedule_events e WHERE e.id=legacy_event)))
 RETURNING id INTO change_request;
 SELECT success INTO ok FROM public.dispatch_schedule_decision(change_request,999,'approve');
 ASSERT ok IS FALSE,'Unauthorized legacy removal accepted';
 SELECT success INTO ok FROM public.dispatch_schedule_decision(change_request,101,'reject');
 ASSERT ok IS TRUE,'Legacy rejection failed';
 ASSERT (SELECT enabled FROM public.schedule_events WHERE id=legacy_event),'Rejected legacy removal changed event';
 ASSERT public.gregorian_snapshot(managed_event)=before_state,'Legacy decision changed managed snapshot';

 -- A v2 request cannot be approved through the old low-level decision API.
 change_request:=public.propose_gregorian_change('update','series',managed_event,NULL,
   jsonb_set(data,'{title}','"Synthetic guarded update"'),101);
 SELECT success INTO ok FROM public.process_schedule_decision(change_request,101,'approve');
 ASSERT ok IS FALSE,'Legacy low-level API accepted v2 envelope';
 ASSERT public.gregorian_snapshot(managed_event)=before_state,'Legacy API changed managed request';
 ASSERT (SELECT status='pending' FROM public.schedule_change_requests WHERE id=change_request),
   'Legacy API consumed managed request';
 SELECT success INTO ok FROM public.dispatch_schedule_decision(change_request,101,'approve');
 ASSERT ok IS TRUE,'V2 dispatcher failed after declined legacy call';
 ASSERT (SELECT title='Synthetic guarded update' FROM public.schedule_events WHERE id=managed_event),
   'Managed update missing';
 ASSERT (SELECT title='Synthetic legacy coexistence' FROM public.schedule_events WHERE id=legacy_event),
   'Managed update changed legacy event';

 -- Legacy writes remain guarded while either series has a live send lease.
 INSERT INTO public.schedule_change_requests(action,event_id,requested_by,proposed_data)
 VALUES('update',legacy_event,101,jsonb_build_object('title','Synthetic legacy edit',
  'start_time','08:00','end_time','08:15','timezone','Asia/Kolkata','recurrence','daily',
  'original',(SELECT jsonb_build_object('title',e.title,'start_time',e.start_time,'end_time',e.end_time,
    'recurrence',e.recurrence,'weekdays',e.weekdays,'event_date',e.event_date,
    'timezone',e.timezone,'enabled',e.enabled,'notes',e.notes)
    FROM public.schedule_events e WHERE e.id=legacy_event)))
 RETURNING id INTO change_request;
 SELECT success INTO ok FROM public.dispatch_schedule_decision(change_request,101,'approve');
 ASSERT ok IS TRUE,'Legacy update no longer works';
 ASSERT public.gregorian_snapshot(managed_event)->'event'->>'title'='Synthetic guarded update',
   'Legacy update changed managed series';
 INSERT INTO public.schedule_change_requests(action,event_id,requested_by,proposed_data)
 VALUES('update',legacy_event,101,jsonb_build_object('title','Synthetic stale edit',
  'start_time','08:00','end_time','08:15','timezone','Asia/Kolkata','recurrence','daily',
  'original',(SELECT jsonb_build_object('title',e.title,'start_time',e.start_time,'end_time',e.end_time,
    'recurrence',e.recurrence,'weekdays',e.weekdays,'event_date',e.event_date,
    'timezone',e.timezone,'enabled',e.enabled,'notes',e.notes)
    FROM public.schedule_events e WHERE e.id=legacy_event))) RETURNING id INTO change_request;
 UPDATE public.schedule_events SET notes='Synthetic concurrent legacy edit' WHERE id=legacy_event;
 SELECT success INTO ok FROM public.dispatch_schedule_decision(change_request,101,'approve');
 ASSERT ok IS FALSE,'Legacy stale snapshot accepted';
 ASSERT (SELECT status='pending' FROM public.schedule_change_requests WHERE id=change_request),
   'Legacy stale request consumed';
 ASSERT (SELECT title='Synthetic legacy edit' FROM public.schedule_events WHERE id=legacy_event),
   'Legacy stale request changed event';
 -- Anchor a due lease directly in the disposable ledger so wall-clock time
 -- does not determine whether the in-flight edit protection is exercised.
 INSERT INTO public.reminder_deliveries(event_id,occurrence_date,status,managed_by,due_at,
   payload,attempts,retry_at,worker_token,lease_until)
 VALUES(legacy_event,test_day,'sending','m2e',now(),'{}',1,now(),gen_random_uuid(),now()+interval '1 minute');
 INSERT INTO public.schedule_change_requests(action,event_id,requested_by,proposed_data)
 VALUES('remove',legacy_event,101,jsonb_build_object('original',
   (SELECT jsonb_build_object('title',e.title,'start_time',e.start_time,'end_time',e.end_time,
    'recurrence',e.recurrence,'weekdays',e.weekdays,'event_date',e.event_date,
    'timezone',e.timezone,'enabled',e.enabled,'notes',e.notes)
    FROM public.schedule_events e WHERE e.id=legacy_event)))
 RETURNING id INTO change_request;
 BEGIN
  SELECT success INTO ok FROM public.dispatch_schedule_decision(change_request,101,'approve');
  ASSERT ok IS FALSE,'Legacy in-flight edit accepted';
 EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL;
 END;
 ASSERT (SELECT enabled FROM public.schedule_events WHERE id=legacy_event),'In-flight legacy event disabled';
 ASSERT (SELECT status='pending' FROM public.schedule_change_requests WHERE id=change_request),
   'In-flight legacy decision consumed request';
 UPDATE public.reminder_deliveries SET lease_until=now()-interval '1 second' WHERE event_id=legacy_event;
 SELECT success INTO ok FROM public.dispatch_schedule_decision(change_request,101,'approve');
 ASSERT ok IS TRUE,'Genuine legacy removal broken after lease ended';
 ASSERT (SELECT NOT enabled FROM public.schedule_events WHERE id=legacy_event),'Legacy removal did not disable event';
 ASSERT public.gregorian_snapshot(managed_event)->'event'->>'title'='Synthetic guarded update',
   'Legacy removal changed managed series';
END $$;
ROLLBACK;
