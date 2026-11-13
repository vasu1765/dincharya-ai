BEGIN;
SET LOCAL plpgsql.check_asserts=on;
DO $$
DECLARE day date:=(now() AT TIME ZONE 'Asia/Kolkata')::date+1;
 data jsonb; edited jsonb; req bigint; stale bigint; ev bigint; other bigint; rule_id bigint;
 ok boolean; clock_at timestamptz; claim record; before_schedule jsonb; before_overrides jsonb;
 history jsonb; ids jsonb; actual date[]; override_before jsonb;
BEGIN
 data:=jsonb_build_object('title','Synthetic series before','start_time','10:00','end_time','10:15',
  'timezone','Asia/Kolkata','recurrence_rule',jsonb_build_object('calendar_system','gregorian',
  'frequency','daily','interval_count',1,'start_date',day,'until_date',day+6));
 req:=public.propose_gregorian_change('add','series',NULL,NULL,data,101);
 SELECT success INTO ok FROM public.dispatch_schedule_decision(req,101,'approve'); ASSERT ok IS TRUE;
 SELECT event_id INTO ev FROM public.schedule_change_requests WHERE id=req;
 SELECT id INTO rule_id FROM public.recurrence_rules WHERE event_id=ev;
 clock_at:=(day+time '00:00') AT TIME ZONE 'Asia/Kolkata';
 PERFORM public.refresh_occurrence_reminders(clock_at,interval '0',interval '7 days');
 ASSERT (SELECT count(*) FROM public.reminder_deliveries WHERE event_id=ev)=7,'Future rows missing';
 SELECT jsonb_object_agg(occurrence_date,id) INTO ids FROM public.reminder_deliveries WHERE event_id=ev;
 -- Install approved exception and cancellation over already-materialized rows.
 req:=public.propose_gregorian_change('update','occurrence',ev,day+2,
  '{"title":"Synthetic unchanged exception","start_time":"13:00","end_time":"13:15","timezone":"Asia/Kolkata"}',101);
 SELECT success INTO ok FROM public.dispatch_schedule_decision(req,101,'approve'); ASSERT ok IS TRUE;
 req:=public.propose_gregorian_change('remove','occurrence',ev,day+3,NULL,101);
 SELECT success INTO ok FROM public.dispatch_schedule_decision(req,101,'approve'); ASSERT ok IS TRUE;
 PERFORM public.refresh_occurrence_reminders(clock_at,interval '0',interval '7 days');
 ASSERT (SELECT status='cancelled' FROM public.reminder_deliveries WHERE event_id=ev AND occurrence_date=day+3);
 SELECT to_jsonb(o) INTO override_before FROM public.generate_event_occurrences(day+2,day+2) o WHERE event_id=ev;
 SELECT jsonb_agg(to_jsonb(o) ORDER BY occurrence_date) INTO before_overrides
  FROM public.schedule_occurrence_overrides o WHERE event_id=ev;
 -- Create sent-with-receipt and uncertain history via normal lease APIs, no HTTP.
 SELECT * INTO claim FROM public.claim_occurrence_reminders(clock_at+interval '10 hours',1);
 ASSERT claim.event_id=ev;
 ASSERT public.acknowledge_occurrence_reminder(claim.delivery_id,claim.worker_token,'sent',
  clock_at+interval '10 hours',101,501);
 SELECT * INTO claim FROM public.claim_occurrence_reminders(clock_at+interval '34 hours',1);
 ASSERT claim.event_id=ev;
 ASSERT public.finish_occurrence_reminder(claim.delivery_id,claim.worker_token,'uncertain',clock_at+interval '34 hours');
 SELECT jsonb_agg(to_jsonb(d) ORDER BY occurrence_date) INTO history FROM public.reminder_deliveries d
  WHERE event_id=ev AND status IN ('sent','uncertain');
 ASSERT jsonb_array_length(history)=2,'Terminal history fixture missing';
 -- A separate approved event conflicts only with the proposed new series time.
 req:=public.propose_gregorian_change('add','series',NULL,NULL,jsonb_build_object(
  'title','Synthetic explicit conflict','start_time','11:00','end_time','11:15','timezone','Asia/Kolkata',
  'recurrence_rule',jsonb_build_object('calendar_system','gregorian','frequency','once',
  'interval_count',1,'start_date',day+4)),101);
 SELECT success INTO ok FROM public.dispatch_schedule_decision(req,101,'approve'); ASSERT ok IS TRUE;
 SELECT event_id INTO other FROM public.schedule_change_requests WHERE id=req;
 edited:=jsonb_set(jsonb_set(jsonb_set(jsonb_set(data,'{title}','"Synthetic series after"'),
  '{start_time}','"11:00"'),'{end_time}','"11:15"'),'{recurrence_rule,interval_count}','2');
 stale:=public.propose_gregorian_change('update','series',ev,NULL,edited,101);
 req:=public.propose_gregorian_change('update','series',ev,NULL,edited,101);
 before_schedule:=public.gregorian_snapshot(ev);
 SELECT success INTO ok FROM public.dispatch_schedule_decision(req,999,'approve',true);
 ASSERT ok IS FALSE,'Foreign requester forced series change';
 SELECT success INTO ok FROM public.dispatch_schedule_decision(req,101,'approve');
 ASSERT ok IS FALSE,'Conflict accepted without explicit approval';
 ASSERT public.gregorian_snapshot(ev)=before_schedule,'Conflict partially changed rule or overrides';
 ASSERT (SELECT status='pending' FROM public.schedule_change_requests WHERE id=req),'Conflict consumed request';
 SELECT success INTO ok FROM public.dispatch_schedule_decision(req,101,'approve',true);
 ASSERT ok IS TRUE,'Explicit conflict approval rejected';
 ASSERT (SELECT id=rule_id FROM public.recurrence_rules WHERE event_id=ev),'Rule identity changed';
 before_schedule:=public.gregorian_snapshot(ev);
 SELECT success INTO ok FROM public.dispatch_schedule_decision(stale,101,'approve',true);
 ASSERT ok IS FALSE,'Stale series approval bypassed snapshot';
 ASSERT public.gregorian_snapshot(ev)=before_schedule,'Stale decision changed series';
 ASSERT (SELECT jsonb_agg(to_jsonb(o) ORDER BY occurrence_date) FROM public.schedule_occurrence_overrides o
  WHERE event_id=ev)=before_overrides,'Series edit rewrote overrides/cancellation';
 SELECT array_agg(occurrence_date ORDER BY occurrence_date) INTO actual
  FROM public.generate_event_occurrences(day,day+6) WHERE event_id=ev;
 ASSERT actual=ARRAY[day,day+2,day+4,day+6],'Edited interval expansion incorrect';
 ASSERT (SELECT to_jsonb(o) FROM public.generate_event_occurrences(day+2,day+2) o WHERE event_id=ev)=override_before,
  'Unaffected occurrence exception changed';
 PERFORM public.refresh_occurrence_reminders(clock_at+interval '34 hours',interval '7 days',interval '7 days');
 ASSERT (SELECT jsonb_object_agg(occurrence_date,id) FROM public.reminder_deliveries WHERE event_id=ev)=ids,
  'Series edit replaced occurrence ledger identities';
 ASSERT (SELECT jsonb_agg(to_jsonb(d) ORDER BY occurrence_date) FROM public.reminder_deliveries d
  WHERE event_id=ev AND status IN ('sent','uncertain'))=history,'Terminal history rewritten';
 ASSERT (SELECT status='cancelled' FROM public.reminder_deliveries WHERE event_id=ev AND occurrence_date=day+5),
  'Removed future recurrence remained pending';
 ASSERT (SELECT status='pending' AND due_at=((day+4)+time '11:00') AT TIME ZONE 'Asia/Kolkata'
  FROM public.reminder_deliveries WHERE event_id=ev AND occurrence_date=day+4),'Retained future work not replanned';
 -- Returning to daily reactivates ordinary cancelled future work but not an
 -- explicit occurrence cancellation; stored exception and terminal history stay.
 edited:=jsonb_set(edited,'{recurrence_rule,interval_count}','1');
 req:=public.propose_gregorian_change('update','series',ev,NULL,edited,101);
 SELECT success INTO ok FROM public.dispatch_schedule_decision(req,101,'approve',true); ASSERT ok IS TRUE;
 PERFORM public.refresh_occurrence_reminders(clock_at+interval '34 hours',interval '7 days',interval '7 days');
 ASSERT NOT EXISTS(SELECT FROM public.generate_event_occurrences(day+3,day+3) WHERE event_id=ev),
  'Dormant explicit cancellation was lost';
 ASSERT (SELECT status='pending' AND attempts=0 FROM public.reminder_deliveries WHERE event_id=ev AND occurrence_date=day+5),
  'Safe future reactivation missing';
 ASSERT (SELECT jsonb_object_agg(occurrence_date,id) FROM public.reminder_deliveries WHERE event_id=ev)=ids;
 ASSERT (SELECT jsonb_agg(to_jsonb(d) ORDER BY occurrence_date) FROM public.reminder_deliveries d
  WHERE event_id=ev AND status IN ('sent','uncertain'))=history;
END $$;
ROLLBACK;
