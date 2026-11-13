BEGIN;
SET LOCAL plpgsql.check_asserts=on;
DO $$
DECLARE ev bigint; too_old bigint; delivery record; prior_payload jsonb;
 clock_at timestamptz:=date_trunc('minute',now());
BEGIN
 -- Recovery includes the exact lookback edge, excludes one second beyond it.
 INSERT INTO public.schedule_events(title,start_time,recurrence,event_date)
 VALUES('Synthetic recovery edge',((clock_at-interval '6 hours') AT TIME ZONE 'Asia/Kolkata')::time,
 'once',((clock_at-interval '6 hours') AT TIME ZONE 'Asia/Kolkata')::date) RETURNING id INTO ev;
 INSERT INTO public.schedule_events(title,start_time,recurrence,event_date)
 VALUES('Synthetic recovery outside',((clock_at-interval '6 hours 1 second') AT TIME ZONE 'Asia/Kolkata')::time,
 'once',((clock_at-interval '6 hours 1 second') AT TIME ZONE 'Asia/Kolkata')::date) RETURNING id INTO too_old;
 SELECT * INTO delivery FROM public.claim_occurrence_reminders(clock_at,1,interval '10 seconds');
 ASSERT delivery.event_id=ev,'Inclusive recovery edge missing';
 ASSERT NOT EXISTS(SELECT FROM public.reminder_deliveries WHERE event_id=too_old),'Outside lookback recovered';
 -- At expiry, quarantine clears the token; the old worker cannot acknowledge.
 PERFORM public.refresh_occurrence_reminders(clock_at+interval '10 seconds');
 ASSERT (SELECT status='uncertain' AND worker_token IS NULL AND lease_until IS NULL
   FROM public.reminder_deliveries WHERE id=delivery.delivery_id),'Exact expiry not quarantined';
 ASSERT public.finish_occurrence_reminder(delivery.delivery_id,delivery.worker_token,'sent',
   clock_at+interval '10 seconds') IS FALSE,'Stale acknowledgement accepted';
 SELECT payload INTO prior_payload FROM public.reminder_deliveries WHERE id=delivery.delivery_id;
 UPDATE public.schedule_events SET title='Synthetic changed after expiry',enabled=false WHERE id=ev;
 PERFORM public.refresh_occurrence_reminders(clock_at+interval '1 day');
 ASSERT (SELECT status='uncertain' AND attempts=1 AND payload=prior_payload
   FROM public.reminder_deliveries WHERE id=delivery.delivery_id),'Quarantine rewritten by schedule/outage';
 ASSERT NOT EXISTS(SELECT FROM public.claim_occurrence_reminders(clock_at+interval '1 day',1)),
   'Quarantined occurrence automatically replayed';
END $$;
DO $$
DECLARE ev bigint; delivery record; identity bigint; old_payload jsonb;
 clock_at timestamptz:=date_trunc('minute',now());
BEGIN
 INSERT INTO public.schedule_events(title,start_time,recurrence,event_date)
 VALUES('Synthetic recovery acknowledged',(clock_at AT TIME ZONE 'Asia/Kolkata')::time,
 'once',(clock_at AT TIME ZONE 'Asia/Kolkata')::date) RETURNING id INTO ev;
 SELECT * INTO delivery FROM public.claim_occurrence_reminders(clock_at,1);
 ASSERT delivery.event_id=ev,'Sent history setup claim missing';
 ASSERT public.finish_occurrence_reminder(delivery.delivery_id,delivery.worker_token,'sent',clock_at),
   'Sent history setup acknowledgement failed';
 SELECT payload INTO old_payload FROM public.reminder_deliveries WHERE id=delivery.delivery_id;
 UPDATE public.schedule_events SET title='Synthetic edit after acknowledgement',enabled=false WHERE id=ev;
 PERFORM public.refresh_occurrence_reminders(clock_at+interval '1 minute');
 ASSERT (SELECT status='sent' AND attempts=1 AND payload=old_payload AND sent_at IS NOT NULL
  FROM public.reminder_deliveries WHERE id=delivery.delivery_id),'Sent history rewritten by edit';

 -- Keep both replanned times on one occurrence date even near real midnight.
 clock_at:=(((clock_at AT TIME ZONE 'Asia/Kolkata')::date+1)+time '12:00') AT TIME ZONE 'Asia/Kolkata';
 INSERT INTO public.schedule_events(title,start_time,recurrence,event_date)
 VALUES('Synthetic replan',((clock_at+interval '10 minutes') AT TIME ZONE 'Asia/Kolkata')::time,
 'once',((clock_at+interval '10 minutes') AT TIME ZONE 'Asia/Kolkata')::date) RETURNING id INTO ev;
 PERFORM public.refresh_occurrence_reminders(clock_at);
 SELECT id INTO identity FROM public.reminder_deliveries WHERE event_id=ev;
 ASSERT identity IS NOT NULL,'Replan setup missing';
 UPDATE public.schedule_events SET enabled=false WHERE id=ev;
 PERFORM public.refresh_occurrence_reminders(clock_at);
 ASSERT (SELECT status='cancelled' FROM public.reminder_deliveries WHERE id=identity),'Replan cancellation missing';
 UPDATE public.schedule_events SET enabled=true,title='Synthetic replanned',
 start_time=((clock_at+interval '20 minutes') AT TIME ZONE 'Asia/Kolkata')::time,
 event_date=((clock_at+interval '20 minutes') AT TIME ZONE 'Asia/Kolkata')::date WHERE id=ev;
 PERFORM public.refresh_occurrence_reminders(clock_at);
 ASSERT (SELECT id=identity AND status='pending' AND attempts=0 AND due_at=clock_at+interval '20 minutes'
  AND payload->>'title'='Synthetic replanned' FROM public.reminder_deliveries WHERE event_id=ev),
  'Replan lost stable identity or kept stale work';
 ASSERT NOT EXISTS(SELECT FROM public.claim_occurrence_reminders(clock_at+interval '10 minutes',1)),
  'Replanned delivery claimed at old due time';
END $$;
ROLLBACK;
