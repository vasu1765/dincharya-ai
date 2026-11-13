BEGIN;
SET LOCAL plpgsql.check_asserts=on;
DO $$ BEGIN
 ASSERT NOT EXISTS(SELECT FROM pg_hba_file_rules WHERE error IS NOT NULL
  OR (type LIKE 'host%' AND auth_method<>'scram-sha-256')
  OR (auth_method='trust' AND type<>'local')),'Authentication boundary changed';
 ASSERT (SELECT NOT enabled FROM reconcile_private.gate),'Reconciliation was enabled';
 ASSERT NOT EXISTS(SELECT FROM reconcile_private.audit),'Recurrence fixtures changed audit';
 ASSERT NOT has_table_privilege('dincharya_reminder_worker','public.reminder_deliveries','UPDATE'),
  'Worker gained direct ledger writes';
 ASSERT NOT pg_has_role('dincharya_reminder_worker','dincharya_reconcile_operator','member'),
  'Worker gained operator membership';
END $$;
DO $$
DECLARE item record; data jsonb; req bigint; ev bigint; ok boolean; actual date[];
 old_count bigint; rejected boolean; bad jsonb;
BEGIN
 -- Literal expected dates are independent of the recurrence predicate.
 FOR item IN SELECT * FROM (VALUES
 ('Synthetic weekly cross-year','08:00','2032-12-29','2033-01-26',
  '{"frequency":"weekly","interval_count":2,"weekdays":[1,3]}'::jsonb,
  ARRAY['2032-12-29','2033-01-10','2033-01-12','2033-01-24','2033-01-26']::date[]),
 ('Synthetic yearly cross-year','09:00','2031-12-31','2035-01-31',
  '{"frequency":"yearly","interval_count":2,"months":[1,12],"month_days":[1,31]}'::jsonb,
  ARRAY['2031-12-31','2033-01-01','2033-01-31','2033-12-01','2033-12-31','2035-01-01','2035-01-31']::date[]),
 ('Synthetic monthly selectors','10:00','2031-12-30','2032-04-30',
  '{"frequency":"monthly","interval_count":2,"month_days":[29,30,31]}'::jsonb,
  ARRAY['2031-12-30','2031-12-31','2032-02-29','2032-04-29','2032-04-30']::date[]),
 ('Synthetic yearly leap selectors','11:00','2031-02-28','2033-02-28',
  '{"frequency":"yearly","interval_count":1,"months":[2],"month_days":[28,29]}'::jsonb,
  ARRAY['2031-02-28','2032-02-28','2032-02-29','2033-02-28']::date[]),
 ('Synthetic Gregorian century','12:00','2096-02-29','2104-02-29',
  '{"frequency":"yearly","interval_count":4,"months":[2],"month_days":[29]}'::jsonb,
  ARRAY['2096-02-29','2104-02-29']::date[])
 ) AS cases(title,slot,first_day,last_day,rule,expected)
 LOOP
  data:=jsonb_build_object('title',item.title,'start_time',item.slot,'timezone','Asia/Kolkata',
   'recurrence_rule',item.rule||jsonb_build_object('calendar_system','gregorian',
    'start_date',item.first_day,'until_date',item.last_day));
  SELECT count(*) INTO old_count FROM public.schedule_events;
  req:=public.propose_gregorian_change('add','series',NULL,NULL,data,101);
  ASSERT (SELECT count(*) FROM public.schedule_events)=old_count,'Proposal mutated schedule';
  ASSERT (SELECT status='pending' FROM public.schedule_change_requests WHERE id=req),'Approval was bypassed';
  SELECT success INTO ok FROM public.dispatch_schedule_decision(req,101,'approve');
  ASSERT ok IS TRUE,'Calendar proposal approval failed';
  SELECT event_id INTO ev FROM public.schedule_change_requests WHERE id=req;
  SELECT array_agg(occurrence_date ORDER BY occurrence_date) INTO actual
   FROM public.generate_event_occurrences(item.first_day::date-1,item.last_day::date+366) WHERE event_id=ev;
  ASSERT actual=item.expected,'Calendar API expansion differs from literal expected dates';
  ASSERT (SELECT count(*) FROM public.generate_event_occurrences(item.first_day::date,item.first_day::date)
   WHERE event_id=ev)=1,'Inclusive start boundary missing';
  ASSERT (SELECT count(*) FROM public.generate_event_occurrences(item.last_day::date,item.last_day::date)
   WHERE event_id=ev)=1,'Inclusive until boundary missing';
  SELECT success INTO ok FROM public.dispatch_schedule_decision(req,101,'approve');
  ASSERT ok IS FALSE,'Approval replay changed identity';
 END LOOP;
 -- Invalid concrete dates and selector ranges must reject the whole proposal.
 data:='{"title":"Synthetic invalid calendar","start_time":"14:00","timezone":"Asia/Kolkata","recurrence_rule":{"calendar_system":"gregorian","frequency":"yearly","interval_count":1,"start_date":"2032-02-29","months":[2],"month_days":[29]}}';
 FOR bad IN SELECT value FROM jsonb_array_elements(jsonb_build_array(
   jsonb_set(data,'{recurrence_rule,start_date}','"2033-02-29"'),
   jsonb_set(data,'{recurrence_rule,start_date}','"2032-02-30"'),
   jsonb_set(data,'{recurrence_rule,until_date}','"2033-02-29"'),
   jsonb_set(data,'{recurrence_rule,until_date}','"2031-12-31"'),
   jsonb_set(data,'{recurrence_rule,months}','[2,13]'),
   jsonb_set(data,'{recurrence_rule,month_days}','[29,32]')))
 LOOP
  SELECT count(*) INTO old_count FROM public.schedule_change_requests;
  rejected:=false;
  BEGIN PERFORM public.propose_gregorian_change('add','series',NULL,NULL,bad,101);
  EXCEPTION WHEN data_exception THEN rejected:=true; END;
  ASSERT rejected,'Invalid calendar API proposal accepted';
  ASSERT (SELECT count(*) FROM public.schedule_change_requests)=old_count,'Invalid proposal persisted';
 END LOOP;
END $$;
ROLLBACK;
