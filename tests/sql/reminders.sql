BEGIN;
SET LOCAL plpgsql.check_asserts=on;
DO $$
DECLARE ev bigint; ev2 bigint; row record; amount int; now_at timestamptz:=date_trunc('minute',now());
 local_day date; local_time time; request bigint; ok boolean; blocked boolean:=false;
 data jsonb; attempt int; retry_clock timestamptz;
BEGIN
 local_day:=(now_at AT TIME ZONE 'Asia/Kolkata')::date;
 local_time:=(now_at AT TIME ZONE 'Asia/Kolkata')::time;
 INSERT INTO public.schedule_events(title,start_time,recurrence,event_date)
 VALUES('Synthetic reminder',local_time,'once',local_day) RETURNING id INTO ev;
 PERFORM public.refresh_occurrence_reminders(now_at);
 PERFORM public.refresh_occurrence_reminders(now_at);
 ASSERT (SELECT count(*) FROM public.reminder_deliveries WHERE event_id=ev)=1,'Materialization duplicated delivery';
 SELECT * INTO row FROM public.claim_occurrence_reminders(now_at,1);
 ASSERT row.event_id=ev AND row.worker_token IS NOT NULL,'Claim failed';
 ASSERT NOT EXISTS(SELECT FROM public.claim_occurrence_reminders(now_at,1)),'Double claim';
 ASSERT NOT public.finish_occurrence_reminder(row.delivery_id,gen_random_uuid(),'sent',now_at),'Wrong worker token accepted';
 BEGIN UPDATE public.schedule_events SET title='Concurrent edit' WHERE id=ev;
 EXCEPTION WHEN object_not_in_prerequisite_state THEN blocked:=true; END;
 ASSERT blocked,'In-flight schedule edit accepted';
 ASSERT public.finish_occurrence_reminder(row.delivery_id,row.worker_token,'not_accepted',now_at),'Retry outcome';
 ASSERT NOT EXISTS(SELECT FROM public.claim_occurrence_reminders(now_at+interval '10 seconds',1)),'Backoff ignored';
 SELECT * INTO row FROM public.claim_occurrence_reminders(now_at+interval '31 seconds',1);
 ASSERT row.worker_token IS NOT NULL,'Retry missing';
 ASSERT public.finish_occurrence_reminder(row.delivery_id,row.worker_token,'sent',now_at+interval '32 seconds'),'Send acknowledgement';
 ASSERT NOT public.finish_occurrence_reminder(row.delivery_id,row.worker_token,'sent',now_at+interval '33 seconds'),'Acknowledgement replay';
 ASSERT NOT EXISTS(SELECT FROM public.claim_occurrence_reminders(now_at+interval '1 minute',1)),'Sent occurrence redelivered';
 -- A legacy ledger row suppresses duplicate delivery and remains untouched.
 INSERT INTO public.schedule_events(title,start_time,recurrence,event_date)
 VALUES('Synthetic legacy ledger',local_time,'once',local_day) RETURNING id INTO ev2;
 INSERT INTO public.reminder_deliveries(event_id,occurrence_date,status) VALUES(ev2,local_day,'sent');
 PERFORM public.refresh_occurrence_reminders(now_at);
 ASSERT (SELECT managed_by IS NULL AND due_at IS NULL FROM public.reminder_deliveries WHERE event_id=ev2),'Legacy history rewritten';
 -- Lost acknowledgement/crash is quarantined instead of blindly retried.
 INSERT INTO public.schedule_events(title,start_time,recurrence,event_date)
 VALUES('Synthetic uncertain',local_time,'once',local_day) RETURNING id INTO ev2;
 SELECT * INTO row FROM public.claim_occurrence_reminders(now_at,1,interval '10 seconds');
 ASSERT row.event_id=ev2,'Uncertain test claim';
 PERFORM public.refresh_occurrence_reminders(now_at+interval '11 seconds');
 ASSERT (SELECT status='uncertain' FROM public.reminder_deliveries WHERE id=row.delivery_id),'Expired lease not quarantined';
 ASSERT NOT public.finish_occurrence_reminder(row.delivery_id,row.worker_token,'sent',now_at+interval '12 seconds'),'Expired worker accepted';
 ASSERT NOT EXISTS(SELECT FROM public.claim_occurrence_reminders(now_at+interval '13 seconds',1)),'Uncertain send retried';
 -- A pending proposal has no delivery. Explicit owner approval makes it eligible.
 data:=jsonb_build_object('title','Synthetic approved reminder','start_time',local_time,
   'end_time',NULL,'timezone','Asia/Kolkata','recurrence_rule',
   jsonb_build_object('calendar_system','gregorian','frequency','once','interval_count',1,'start_date',local_day));
 -- Give this proposal a distinct minute from existing synthetic events.
 data:=jsonb_set(data,'{start_time}',to_jsonb(to_char((now_at + interval '1 minute') AT TIME ZONE 'Asia/Kolkata','HH24:MI')));
 retry_clock:=now_at+interval '1 minute';
 data:=jsonb_set(data,'{recurrence_rule,start_date}',
   to_jsonb((retry_clock AT TIME ZONE 'Asia/Kolkata')::date));
 request:=public.propose_gregorian_change('add','series',NULL,NULL,data,101);
 ASSERT NOT EXISTS(SELECT FROM public.claim_occurrence_reminders(retry_clock,1)),'Pending proposal was claimable';
 SELECT success INTO ok FROM public.decide_gregorian_change(request,101,'approve');
 ASSERT ok,'Reminder approval failed';
 SELECT event_id INTO ev2 FROM public.schedule_change_requests WHERE id=request;
 FOR attempt IN 1..5 LOOP
    SELECT * INTO row FROM public.claim_occurrence_reminders(retry_clock,1);
    ASSERT row.event_id=ev2,'Approved reminder claim missing';
    ASSERT public.finish_occurrence_reminder(row.delivery_id,row.worker_token,'not_accepted',retry_clock),
      'Confirmed rejection failed';
    retry_clock:=retry_clock+interval '5 minutes';
 END LOOP;
 ASSERT (SELECT status='dead' AND attempts=5 FROM public.reminder_deliveries WHERE id=row.delivery_id),
   'Retry cap did not mark delivery dead';
 ASSERT NOT EXISTS(SELECT FROM public.claim_occurrence_reminders(retry_clock,1)),'Dead delivery reclaimed';
 -- Recovery bounded by lookback; cancellation preserves identity/history.
 INSERT INTO public.schedule_events(title,start_time,recurrence,event_date)
 VALUES('Synthetic old',local_time,'once',local_day-2) RETURNING id INTO ev2;
 PERFORM public.refresh_occurrence_reminders(now_at);
 ASSERT NOT EXISTS(SELECT FROM public.reminder_deliveries WHERE event_id=ev2),'Outage window ignored';
 INSERT INTO public.schedule_events(title,start_time,recurrence,event_date)
 VALUES('Synthetic cancellation',local_time,'once',local_day) RETURNING id INTO ev2;
 PERFORM public.refresh_occurrence_reminders(now_at);
 UPDATE public.schedule_events SET enabled=false WHERE id=ev2;
 PERFORM public.refresh_occurrence_reminders(now_at);
 ASSERT (SELECT status='cancelled' FROM public.reminder_deliveries WHERE event_id=ev2),'Disabled event queued';
END $$;
ROLLBACK;
