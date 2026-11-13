BEGIN;
SET LOCAL plpgsql.check_asserts=on;
DO $$
DECLARE data jsonb; req bigint; ev bigint; pending_update bigint; pending_remove bigint; pending_tagged bigint;
 ok boolean; reason text; snapshot jsonb; managed_snapshot jsonb; blocked boolean;
 day date := (now() AT TIME ZONE 'Asia/Kolkata')::date;
BEGIN
 INSERT INTO public.schedule_events(title,start_time,end_time,recurrence,timezone)
 VALUES('Synthetic transition','10:00','10:15','daily','Asia/Kolkata') RETURNING id INTO ev;
 SELECT jsonb_build_object('title',e.title,'start_time',e.start_time,'end_time',e.end_time,
  'recurrence',e.recurrence,'weekdays',e.weekdays,'event_date',e.event_date,
  'timezone',e.timezone,'enabled',e.enabled,'notes',e.notes)
 INTO snapshot FROM public.schedule_events e WHERE e.id=ev;
 INSERT INTO public.schedule_change_requests(action,event_id,requested_by,proposed_data)
 VALUES('update',ev,101,jsonb_build_object('title','Synthetic stale legacy change',
  'start_time','10:00','end_time','10:15','timezone','Asia/Kolkata',
  'recurrence','daily','original',snapshot)) RETURNING id INTO pending_update;
 INSERT INTO public.schedule_change_requests(action,event_id,requested_by,proposed_data)
 VALUES('remove',ev,101,jsonb_build_object('original',snapshot)) RETURNING id INTO pending_remove;
 -- A version tag alone must not turn the legacy decision entry point into a
 -- bypass. This deliberately malformed v2-tagged legacy envelope is untrusted.
 INSERT INTO public.schedule_change_requests(action,event_id,requested_by,proposed_data)
 VALUES('update',ev,101,jsonb_build_object('api_version',2,'title','Synthetic forged version tag',
  'start_time','10:00','end_time','10:15','timezone','Asia/Kolkata','recurrence','daily','original',snapshot))
 RETURNING id INTO pending_tagged;
 data:=jsonb_build_object('title','Synthetic transition','start_time','10:00',
  'end_time','10:15','timezone','Asia/Kolkata','recurrence_rule',jsonb_build_object(
    'calendar_system','gregorian','frequency','daily','interval_count',1,'start_date',day));
 req:=public.propose_gregorian_change('update','series',ev,NULL,data,101);
 SELECT success INTO ok FROM public.dispatch_schedule_decision(req,101,'approve');
 ASSERT ok IS TRUE,'Legacy-to-managed conversion failed';
 ASSERT (SELECT rule_options->>'managed_by'='m2d' FROM public.recurrence_rules WHERE event_id=ev),
   'Conversion did not establish managed ownership';
 req:=public.propose_gregorian_change('update','occurrence',ev,day,
  '{"title":"Synthetic override","start_time":"11:00","end_time":"11:15","timezone":"Asia/Kolkata"}',101);
 SELECT success INTO ok FROM public.dispatch_schedule_decision(req,101,'approve');
 ASSERT ok IS TRUE,'Managed override failed';
 managed_snapshot:=public.gregorian_snapshot(ev);

 -- Authorization must run before compatibility diagnostics; no private state leaks.
 SELECT success,message INTO ok,reason FROM public.process_schedule_decision(pending_update,999,'approve');
 ASSERT ok IS FALSE AND reason NOT LIKE 'Managed series%', 'Unauthorized compatibility disclosure';
 FOREACH req IN ARRAY ARRAY[pending_update,pending_remove,pending_tagged] LOOP
  SELECT success,message INTO ok,reason FROM public.process_schedule_decision(req,101,'approve',true);
  ASSERT ok IS FALSE AND reason='Managed series requires a fresh v2 proposal',
   'Direct legacy mutation bypassed managed boundary';
  SELECT success,message INTO ok,reason FROM public.dispatch_schedule_decision(req,101,'approve',true);
  ASSERT ok IS FALSE,'Dispatcher legacy mutation bypassed managed boundary';
  IF req<>pending_tagged THEN
   ASSERT reason='Managed series requires a fresh v2 proposal','Dispatcher compatibility reason changed';
  END IF;
  ASSERT (SELECT status='pending' FROM public.schedule_change_requests WHERE id=req),
   'Blocked legacy request consumed';
  ASSERT public.gregorian_snapshot(ev)=managed_snapshot,'Blocked legacy mutation changed managed state';
 END LOOP;
 SELECT success INTO ok FROM public.process_schedule_decision(pending_remove,101,' APPROVE ',true);
 ASSERT ok IS FALSE,'Noncanonical approval bypassed managed boundary';
 ASSERT public.gregorian_snapshot(ev)=managed_snapshot,'Noncanonical decision changed managed state';

 -- Both official submission and direct legacy envelopes are blocked immediately.
 FOREACH reason IN ARRAY ARRAY['update','remove'] LOOP
  blocked:=false;
  BEGIN
   PERFORM public.create_schedule_change_proposal(reason,ev,101,'Synthetic new legacy','10:00','10:15');
  EXCEPTION WHEN invalid_parameter_value THEN blocked:=true;
  END;
  ASSERT blocked,'Official legacy submission accepted managed target';
  blocked:=false;
  BEGIN
   INSERT INTO public.schedule_change_requests(action,event_id,requested_by,proposed_data)
   VALUES(reason,ev,101,jsonb_build_object('original',snapshot));
  EXCEPTION WHEN invalid_parameter_value THEN blocked:=true;
  END;
  ASSERT blocked,'Direct legacy envelope accepted managed target';
 END LOOP;
 ASSERT public.gregorian_snapshot(ev)=managed_snapshot,'Blocked submission mutated managed state';
 -- Owners can discard an old request and continue through mandatory v2 approval.
 SELECT success INTO ok FROM public.process_schedule_decision(pending_update,101,'reject');
 ASSERT ok IS TRUE,'Owner could not discard blocked legacy request';
 req:=public.propose_gregorian_change('update','series',ev,NULL,
   jsonb_set(data,'{title}','"Synthetic approved v2 update"'),101);
 ASSERT public.gregorian_snapshot(ev)=managed_snapshot,'V2 proposal mutated managed state before approval';
 SELECT success INTO ok FROM public.dispatch_schedule_decision(req,999,'approve');
 ASSERT ok IS FALSE,'Unauthorized v2 decision accepted';
 SELECT success INTO ok FROM public.dispatch_schedule_decision(req,101,'approve');
 ASSERT ok IS TRUE,'V2 series update broken by legacy boundary';
 SELECT success INTO ok FROM public.dispatch_schedule_decision(req,101,'approve');
 ASSERT ok IS FALSE,'V2 replay accepted after legacy boundary';
END $$;
ROLLBACK;
