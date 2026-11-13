BEGIN;
SET LOCAL plpgsql.check_asserts=on;
-- All records and identities below are invented. No baseline rows are copied.
DO $$
DECLARE data jsonb; request bigint; ev bigint; ok boolean; amount int; orig jsonb; rule public.recurrence_rules;
BEGIN
 data:='{"title":"Synthetic monthly","start_time":"10:00","end_time":"11:00","timezone":"Asia/Kolkata","recurrence_rule":{"calendar_system":"gregorian","frequency":"monthly","interval_count":1,"start_date":"2032-01-31","month_days":[31]}}';
 request:=public.propose_gregorian_change('add','series',NULL,NULL,data,101);
 SELECT success INTO ok FROM public.dispatch_schedule_decision(request,999,'approve'); ASSERT NOT ok,'Unauthorized approval';
 ASSERT NOT EXISTS(SELECT FROM public.schedule_events),'Proposal mutated schedule';
 SELECT success INTO ok FROM public.dispatch_schedule_decision(request,101,'approve'); ASSERT ok,'Monthly approval';
 SELECT event_id INTO ev FROM public.schedule_change_requests WHERE id=request;
 SELECT count(*) INTO amount FROM public.generate_event_occurrences('2032-01-01','2032-03-31'); ASSERT amount=2,'Invalid month day must skip February';
 SELECT success INTO ok FROM public.dispatch_schedule_decision(request,101,'approve'); ASSERT NOT ok,'Duplicate decision';
 -- Occurrence update preserves the series and stable original date identity.
 request:=public.propose_gregorian_change('update','occurrence',ev,'2032-03-31',
   '{"title":"Synthetic exception","start_time":"12:00","end_time":null,"timezone":"Asia/Kolkata"}',101);
 SELECT success INTO ok FROM public.dispatch_schedule_decision(request,101,'approve'); ASSERT ok,'Occurrence update';
 ASSERT EXISTS(SELECT FROM public.generate_event_occurrences('2032-03-31','2032-03-31') WHERE event_title='Synthetic exception' AND start_time='12:00'),'Override output';
 ASSERT EXISTS(SELECT FROM public.generate_event_occurrences('2032-01-31','2032-01-31') WHERE start_time='10:00'),'Series mutated by override';
 request:=public.propose_gregorian_change('remove','occurrence',ev,'2032-03-31',NULL,101);
 SELECT success INTO ok FROM public.dispatch_schedule_decision(request,101,'approve'); ASSERT ok,'Occurrence removal';
 ASSERT NOT EXISTS(SELECT FROM public.generate_event_occurrences('2032-03-31','2032-03-31')),'Cancelled occurrence emitted';
 -- Existing occurrence selectors are not assumed correct: test leap/year and ISO-week anchors.
 SELECT * INTO rule FROM public.recurrence_rules WHERE event_id=ev;
 rule.frequency:='yearly'; rule.start_date:='2032-02-29'; rule.month_days:=ARRAY[29]::smallint[]; rule.months:=ARRAY[2]::smallint[];
 ASSERT public.gregorian_rule_matches(rule,'2036-02-29'),'Leap date missing';
 ASSERT NOT public.gregorian_rule_matches(rule,'2033-02-28'),'Leap date clamped unexpectedly';
 rule.frequency:='weekly'; rule.start_date:='2032-01-07'; rule.interval_count:=2; rule.weekdays:=ARRAY[1,3]::smallint[];
 ASSERT public.gregorian_rule_matches(rule,'2032-01-07'),'Anchor Wednesday';
 ASSERT NOT public.gregorian_rule_matches(rule,'2032-01-12'),'ISO week boundary';
 ASSERT public.gregorian_rule_matches(rule,'2032-01-19'),'Second ISO week';
 rule.frequency:='daily'; rule.interval_count:=2; rule.until_date:='2032-01-11';
 ASSERT public.gregorian_rule_matches(rule,'2032-01-11'),'Inclusive until';
 ASSERT NOT public.gregorian_rule_matches(rule,'2032-01-13'),'Until ignored';
 -- Conflict rejection rolls back proposed writes and leaves request pending.
 data:=jsonb_set(data,'{title}','"Synthetic conflict"');
 request:=public.propose_gregorian_change('add','series',NULL,NULL,data,101);
 SELECT success INTO ok FROM public.dispatch_schedule_decision(request,101,'approve'); ASSERT NOT ok,'Conflict accepted';
 ASSERT (SELECT count(*) FROM public.schedule_events)=1,'Conflict rollback leaked event';
 SELECT success INTO ok FROM public.dispatch_schedule_decision(request,101,'approve',true); ASSERT ok,'Explicit override rejected';
 -- Adjacent half-open ranges do not conflict.
 data:=jsonb_set(jsonb_set(data,'{start_time}','"11:00"'),'{end_time}','"12:00"');
 request:=public.propose_gregorian_change('add','series',NULL,NULL,data,101);
 SELECT success INTO ok FROM public.dispatch_schedule_decision(request,101,'approve'); ASSERT ok,'Adjacent range conflict';
 -- Stale snapshot, rejection and series removal.
 request:=public.propose_gregorian_change('update','series',ev,NULL,data,101);
 UPDATE public.schedule_events SET notes='Synthetic concurrent edit' WHERE id=ev;
 SELECT success INTO ok FROM public.dispatch_schedule_decision(request,101,'approve',true); ASSERT NOT ok,'Stale snapshot accepted';
 SELECT success INTO ok FROM public.dispatch_schedule_decision(request,101,'reject'); ASSERT ok,'Rejection';
 request:=public.propose_gregorian_change('remove','series',ev,NULL,NULL,101);
 SELECT success INTO ok FROM public.dispatch_schedule_decision(request,101,'approve'); ASSERT ok,'Series removal';
 ASSERT NOT (SELECT enabled FROM public.schedule_events WHERE id=ev),'Series not disabled';
END $$;
DO $$
DECLARE invalid boolean:=false;
BEGIN
 BEGIN PERFORM public.gregorian_validate('{"title":"Synthetic","start_time":"24:00","timezone":"Asia/Kolkata","recurrence_rule":{"calendar_system":"gregorian","frequency":"daily","interval_count":1,"start_date":"2032-01-01"}}');
 EXCEPTION WHEN invalid_parameter_value THEN invalid:=true; END;
 ASSERT invalid,'Invalid time accepted';
 invalid:=false;
 BEGIN PERFORM public.generate_event_occurrences('2032-01-01','2050-01-01');
 EXCEPTION WHEN invalid_parameter_value THEN invalid:=true; END;
 ASSERT invalid,'Unbounded occurrence window';
 invalid:=false;
 BEGIN PERFORM public.gregorian_validate('{"title":"Synthetic","start_time":"10:00","timezone":"Asia/Kolkata","recurrence_rule":{"calendar_system":"gregorian","frequency":"weekly","interval_count":1,"start_date":"2032-01-01","weekdays":[1,1]}}');
 EXCEPTION WHEN invalid_parameter_value THEN invalid:=true; END;
 ASSERT invalid,'Duplicate selectors accepted';
END $$;
ROLLBACK;
