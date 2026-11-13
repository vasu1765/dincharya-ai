BEGIN;
SET LOCAL plpgsql.check_asserts=on;
DO $$
DECLARE ev bigint; row record; first_id bigint; failed_id bigint; old_body text;
 clock_at timestamptz:=date_trunc('minute',now()); blocked boolean; version text; next_version text;
BEGIN
 -- An expired/wrong token cannot attach a receipt or mark sent.
 INSERT INTO public.schedule_events(title,start_time,recurrence,event_date)
 VALUES('Synthetic stale receipt',(clock_at AT TIME ZONE 'Asia/Kolkata')::time,
 'once',(clock_at AT TIME ZONE 'Asia/Kolkata')::date) RETURNING id INTO ev;
 SELECT * INTO row FROM public.claim_occurrence_reminders(clock_at,1,interval '10 seconds');
 ASSERT row.event_id=ev,'Receipt stale setup claim missing';
 ASSERT NOT public.acknowledge_occurrence_reminder(row.delivery_id,gen_random_uuid(),'sent',clock_at,101,12),
  'Wrong token attached receipt';
 ASSERT NOT public.acknowledge_occurrence_reminder(row.delivery_id,row.worker_token,'sent',clock_at+interval '10 seconds',101,12),
  'Expired lease attached receipt';
 PERFORM public.refresh_occurrence_reminders(clock_at+interval '10 seconds');
 ASSERT (SELECT status='uncertain' AND telegram_chat_id IS NULL AND telegram_message_id IS NULL
  FROM public.reminder_deliveries WHERE id=row.delivery_id),'Expired send was not quarantined without receipt';

 INSERT INTO public.schedule_events(title,start_time,recurrence,event_date)
 VALUES('Synthetic receipt accepted',(clock_at AT TIME ZONE 'Asia/Kolkata')::time,
 'once',(clock_at AT TIME ZONE 'Asia/Kolkata')::date) RETURNING id INTO ev;
 SELECT * INTO row FROM public.claim_occurrence_reminders(clock_at,1);
 ASSERT row.event_id=ev,'Receipt setup claim missing';
 blocked:=false;
 BEGIN PERFORM public.acknowledge_occurrence_reminder(row.delivery_id,row.worker_token,'sent',clock_at,101,NULL);
 EXCEPTION WHEN invalid_parameter_value THEN blocked:=true; END;
 ASSERT blocked,'Partial receipt accepted';
 blocked:=false;
 BEGIN PERFORM public.acknowledge_occurrence_reminder(row.delivery_id,row.worker_token,'uncertain',clock_at,101,12);
 EXCEPTION WHEN invalid_parameter_value THEN blocked:=true; END;
 ASSERT blocked,'Receipt accepted for non-sent outcome';
 ASSERT (SELECT status='sending' AND telegram_chat_id IS NULL FROM public.reminder_deliveries WHERE id=row.delivery_id),
  'Invalid receipt changed send state';
 ASSERT public.acknowledge_occurrence_reminder(row.delivery_id,row.worker_token,'sent',clock_at,101,12),
  'Receipt acknowledgement failed';
 first_id:=row.delivery_id;
 ASSERT (SELECT status='sent' AND attempts=1 AND sent_at=clock_at AND worker_token IS NULL
   AND telegram_chat_id=101 AND telegram_message_id=12 FROM public.reminder_deliveries WHERE id=first_id),
  'Receipt and sent state were not atomically persisted';
 ASSERT NOT public.acknowledge_occurrence_reminder(first_id,row.worker_token,'sent',clock_at,202,99),
  'Receipt acknowledgement replay accepted';
 ASSERT (SELECT telegram_chat_id=101 AND telegram_message_id=12 FROM public.reminder_deliveries WHERE id=first_id),
  'Replay overwrote receipt';

 -- Old workers retain four-argument acknowledgement with nullable receipt.
 INSERT INTO public.schedule_events(title,start_time,recurrence,event_date)
 VALUES('Synthetic old worker receipt',(clock_at AT TIME ZONE 'Asia/Kolkata')::time,
 'once',(clock_at AT TIME ZONE 'Asia/Kolkata')::date) RETURNING id INTO ev;
 SELECT * INTO row FROM public.claim_occurrence_reminders(clock_at,1);
 ASSERT row.event_id=ev,'Old-worker claim missing';
 ASSERT public.finish_occurrence_reminder(row.delivery_id,row.worker_token,'sent',clock_at),'Old ack API changed';
 ASSERT (SELECT status='sent' AND telegram_chat_id IS NULL AND telegram_message_id IS NULL
  FROM public.reminder_deliveries WHERE id=row.delivery_id),'Old worker receipt was invented';

 -- Duplicate external receipt is rejected and rolls back even the sent update.
 INSERT INTO public.schedule_events(title,start_time,recurrence,event_date)
 VALUES('Synthetic duplicate receipt',(clock_at AT TIME ZONE 'Asia/Kolkata')::time,
 'once',(clock_at AT TIME ZONE 'Asia/Kolkata')::date) RETURNING id INTO ev;
 SELECT * INTO row FROM public.claim_occurrence_reminders(clock_at,1);
 ASSERT row.event_id=ev,'Duplicate receipt setup claim missing';
 failed_id:=row.delivery_id; blocked:=false;
 BEGIN PERFORM public.acknowledge_occurrence_reminder(failed_id,row.worker_token,'sent',clock_at,101,12);
 EXCEPTION WHEN unique_violation THEN blocked:=true; END;
 ASSERT blocked,'Duplicate chat/message receipt accepted';
 ASSERT (SELECT status='sending' AND worker_token=row.worker_token AND sent_at IS NULL
   AND telegram_chat_id IS NULL AND telegram_message_id IS NULL FROM public.reminder_deliveries WHERE id=failed_id),
  'Receipt failure partially committed acknowledgement';
 PERFORM public.refresh_occurrence_reminders(clock_at+interval '2 minutes');
 ASSERT (SELECT status='uncertain' FROM public.reminder_deliveries WHERE id=failed_id),
  'Failed acknowledgement did not quarantine on expiry';
 ASSERT NOT EXISTS(SELECT FROM public.claim_occurrence_reminders(clock_at+interval '2 minutes',1)),
  'Failed acknowledgement automatically resent';
 SELECT encode(sha256(convert_to(to_jsonb(d)::text,'UTF8')),'hex') INTO version
  FROM public.reminder_deliveries d WHERE id=failed_id;
 ASSERT version ~ '^[0-9a-f]{64}$','Read-only observation fingerprint invalid';
 UPDATE public.reminder_deliveries SET error_message='Synthetic observation invalidation' WHERE id=failed_id;
 SELECT encode(sha256(convert_to(to_jsonb(d)::text,'UTF8')),'hex') INTO next_version
  FROM public.reminder_deliveries d WHERE id=failed_id;
 ASSERT version<>next_version,'Changed state retained stale reconciliation observation';

 -- Message IDs are scoped to chat, not globally unique.
 INSERT INTO public.schedule_events(title,start_time,recurrence,event_date)
 VALUES('Synthetic other chat receipt',(clock_at AT TIME ZONE 'Asia/Kolkata')::time,
 'once',(clock_at AT TIME ZONE 'Asia/Kolkata')::date) RETURNING id INTO ev;
 SELECT * INTO row FROM public.claim_occurrence_reminders(clock_at,1);
 ASSERT row.event_id=ev,'Other-chat claim missing';
 ASSERT public.acknowledge_occurrence_reminder(row.delivery_id,row.worker_token,'sent',clock_at,202,12),
  'Different chat message-ID reuse rejected';
 ASSERT (SELECT count(*) FROM public.reminder_deliveries WHERE telegram_message_id=12)=2,
  'Receipt chat scope identity failed';
END $$;
ROLLBACK;
