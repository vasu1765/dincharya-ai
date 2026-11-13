BEGIN;
SET LOCAL plpgsql.check_asserts=on;
DO $$
DECLARE base jsonb; bad jsonb; req bigint; ev bigint; ok boolean; unchanged jsonb;
 before_count int; rejected boolean; kind text; horizon int; other bigint; input record;
 day date:=(now() AT TIME ZONE 'Asia/Kolkata')::date+1;
BEGIN
 base:=jsonb_build_object('title','Synthetic adversarial series','start_time','12:00',
  'end_time','12:15','timezone','Asia/Kolkata','recurrence_rule',jsonb_build_object(
  'calendar_system','gregorian','frequency','daily','interval_count',1,'start_date',day));
 -- Invalid public proposal inputs never create requests or events.
 FOR bad IN SELECT value FROM jsonb_array_elements(jsonb_build_array(
   NULL,'[]'::jsonb,base||'{"unexpected":true}',base||'{"timezone":"UTC"}',
   jsonb_set(base,'{recurrence_rule,interval_count}','0'),
   jsonb_set(base,'{recurrence_rule,interval_count}','1001'),
   jsonb_set(base,'{recurrence_rule,start_date}','"infinity"'),
   jsonb_set(base,'{recurrence_rule,calendar_system}','"hindu"'),
   jsonb_set(base,'{recurrence_rule,unknown}','true')))
 LOOP
  SELECT count(*) INTO before_count FROM public.schedule_change_requests;
  rejected:=false;
  BEGIN PERFORM public.propose_gregorian_change('add','series',NULL,NULL,bad,101);
  EXCEPTION WHEN invalid_parameter_value THEN rejected:=true; END;
  ASSERT rejected,'Malformed proposal accepted';
  ASSERT (SELECT count(*) FROM public.schedule_change_requests)=before_count,'Invalid proposal persisted a request';
  ASSERT NOT EXISTS(SELECT FROM public.schedule_events),'Invalid proposal changed schedule';
 END LOOP;
 FOR input IN SELECT * FROM (VALUES
  (NULL::text,'series',NULL::bigint,NULL::date),
  ('replace','series',NULL,NULL),('add',NULL,NULL,NULL),('add','unknown',NULL,NULL),
  ('add','series',999,NULL),('add','series',NULL,day),
  ('update','series',NULL,NULL),('remove','series',999,NULL),
  ('update','occurrence',999,NULL)
 ) AS args(action,scope,event_id,occurrence_date) LOOP
  SELECT count(*) INTO before_count FROM public.schedule_change_requests;
  rejected:=false;
  BEGIN PERFORM public.propose_gregorian_change(input.action,input.scope,input.event_id,
     input.occurrence_date,base,101);
  EXCEPTION WHEN invalid_parameter_value THEN rejected:=true; END;
  ASSERT rejected,'Invalid API action/scope/identity accepted';
  ASSERT (SELECT count(*) FROM public.schedule_change_requests)=before_count,'Invalid API call persisted request';
  ASSERT NOT EXISTS(SELECT FROM public.schedule_events),'Invalid API call changed schedule';
 END LOOP;
 rejected:=false;
 BEGIN PERFORM public.propose_gregorian_change('add','occurrence',NULL,day,base,101);
 EXCEPTION WHEN invalid_parameter_value THEN rejected:=true; END;
 ASSERT rejected,'Invalid add occurrence scope accepted';
 rejected:=false;
 BEGIN PERFORM public.propose_gregorian_change('add','series',NULL,NULL,base,NULL);
 EXCEPTION WHEN invalid_parameter_value THEN rejected:=true; END;
 ASSERT rejected,'Null requester accepted';

 req:=public.propose_gregorian_change('add','series',NULL,NULL,base,101);
 SELECT success INTO ok FROM public.decide_gregorian_change(req,999,'approve',true);
 ASSERT ok IS FALSE,'Force bypassed requester authorization';
 SELECT success INTO ok FROM public.decide_gregorian_change(req,NULL,'reject');
 ASSERT ok IS FALSE,'Null requester rejected someone else proposal';
 SELECT success INTO ok FROM public.decide_gregorian_change(NULL,101,'approve');
 ASSERT ok IS FALSE,'Null request accepted';
 FOREACH horizon IN ARRAY ARRAY[0,3661,NULL::int] LOOP
  SELECT success INTO ok FROM public.decide_gregorian_change(req,101,'approve',true,horizon);
  ASSERT ok IS FALSE,'Invalid horizon accepted';
 END LOOP;
 SELECT success INTO ok FROM public.decide_gregorian_change(req,101,NULL);
 ASSERT ok IS FALSE,'Null decision accepted';
 SELECT success INTO ok FROM public.decide_gregorian_change(req,101,'APPROVE');
 ASSERT ok IS FALSE,'Noncanonical v2 decision accepted';
 ASSERT (SELECT status='pending' AND event_id IS NULL FROM public.schedule_change_requests WHERE id=req),
  'Invalid decision consumed request';
 ASSERT NOT EXISTS(SELECT FROM public.schedule_events),'Invalid decision changed schedule';
 SELECT success INTO ok FROM public.decide_gregorian_change(req,101,'approve');
 ASSERT ok IS TRUE,'Adversarial setup approval failed';
 SELECT event_id INTO ev FROM public.schedule_change_requests WHERE id=req;
 -- Event-only, rule-only and override-only edits all invalidate full snapshots.
 FOREACH kind IN ARRAY ARRAY['event','rule','override'] LOOP
  req:=public.propose_gregorian_change('update','series',ev,NULL,
    jsonb_set(base,'{title}','"Synthetic stale request"'),101);
  IF kind='event' THEN
   UPDATE public.schedule_events SET notes='Synthetic concurrent metadata change' WHERE id=ev;
  ELSIF kind='rule' THEN
   UPDATE public.recurrence_rules SET interval_count=2 WHERE event_id=ev;
  ELSE
   other:=public.propose_gregorian_change('remove','occurrence',ev,day,NULL,101);
   SELECT success INTO ok FROM public.decide_gregorian_change(other,101,'approve');
   ASSERT ok IS TRUE,'Override stale setup failed';
  END IF;
  unchanged:=public.gregorian_snapshot(ev);
  SELECT success INTO ok FROM public.decide_gregorian_change(req,101,'approve',true);
  ASSERT ok IS FALSE,'Force bypassed changed managed snapshot';
  ASSERT public.gregorian_snapshot(ev)=unchanged,'Stale approval partially mutated managed state';
  ASSERT (SELECT status='pending' FROM public.schedule_change_requests WHERE id=req),'Stale request consumed';
  SELECT success INTO ok FROM public.decide_gregorian_change(req,101,'reject');
  ASSERT ok IS TRUE,'Owner could not discard stale request';
  SELECT success INTO ok FROM public.decide_gregorian_change(req,101,'reject');
  ASSERT ok IS FALSE,'Rejection replay accepted';
 END LOOP;
 -- A null force value is not conflict override permission.
 base:=jsonb_set(base,'{recurrence_rule,start_date}',to_jsonb(day+1));
 req:=public.propose_gregorian_change('add','series',NULL,NULL,base,101);
 SELECT success INTO ok FROM public.decide_gregorian_change(req,101,'approve',NULL);
 ASSERT ok IS FALSE,'Null force bypassed conflict check';
 ASSERT (SELECT count(*) FROM public.schedule_events)=1,'Conflict rollback leaked an event';
 ASSERT (SELECT status='pending' FROM public.schedule_change_requests WHERE id=req),'Conflict consumed request';
END $$;
ROLLBACK;
