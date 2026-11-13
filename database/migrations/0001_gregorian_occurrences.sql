-- Additive API over the reviewed schema; never replay the baseline in production.
CREATE TABLE public.schedule_occurrence_overrides (
    event_id bigint NOT NULL REFERENCES public.schedule_events(id),
    occurrence_date date NOT NULL,
    cancelled boolean NOT NULL DEFAULT false,
    title text,
    start_time time,
    end_time time,
    PRIMARY KEY (event_id, occurrence_date),
    CHECK (cancelled OR (title IS NOT NULL AND start_time IS NOT NULL)),
    CHECK (end_time IS NULL OR end_time > start_time)
);

CREATE FUNCTION public.gregorian_validate(p_data jsonb) RETURNS void
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE r jsonb; ok boolean; msg text; until_day date; start_day date; a text; n integer;
BEGIN
    IF jsonb_typeof(p_data) IS DISTINCT FROM 'object' OR EXISTS (
        SELECT FROM jsonb_object_keys(p_data) k
        WHERE k NOT IN ('title','start_time','end_time','timezone','recurrence_rule')
    ) THEN RAISE EXCEPTION 'Invalid schedule fields' USING ERRCODE='22023'; END IF;
    r := p_data->'recurrence_rule';
    IF jsonb_typeof(r) IS DISTINCT FROM 'object' THEN
        RAISE EXCEPTION 'Recurrence object required' USING ERRCODE='22023'; END IF;
    IF EXISTS (SELECT FROM jsonb_object_keys(r) k WHERE k NOT IN
        ('calendar_system','frequency','interval_count','start_date','until_date','weekdays','month_days','months')) THEN
        RAISE EXCEPTION 'Unknown recurrence field' USING ERRCODE='22023'; END IF;
    SELECT v.valid,v.message INTO ok,msg FROM public.validate_schedule_proposal(p_data) v;
    IF ok IS DISTINCT FROM true THEN RAISE EXCEPTION '%',msg USING ERRCODE='22023'; END IF;
    IF (r->>'interval_count')::integer > 1000 OR (p_data->>'start_time')::time >= time '24:00'
       OR (p_data->>'end_time')::time >= time '24:00' THEN
        RAISE EXCEPTION 'Time or interval out of range' USING ERRCODE='22023'; END IF;
    start_day := (r->>'start_date')::date;
    until_day := (r->>'until_date')::date;
    IF NOT isfinite(start_day) OR (until_day IS NOT NULL AND
       (NOT isfinite(until_day) OR until_day < start_day OR r->>'frequency'='once')) THEN
        RAISE EXCEPTION 'Invalid recurrence end date' USING ERRCODE='22023'; END IF;
    FOREACH a IN ARRAY ARRAY['weekdays','month_days','months'] LOOP
        IF r ? a THEN
            IF jsonb_typeof(r->a) IS DISTINCT FROM 'array' THEN
                RAISE EXCEPTION 'Recurrence arrays required' USING ERRCODE='22023'; END IF;
            SELECT count(DISTINCT value) INTO n FROM jsonb_array_elements(r->a);
            IF n <> jsonb_array_length(r->a) THEN
                RAISE EXCEPTION 'Duplicate recurrence selector' USING ERRCODE='22023'; END IF;
        END IF;
    END LOOP;
END $$;

CREATE FUNCTION public.gregorian_rule_matches(p_rule public.recurrence_rules, p_day date)
RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path = pg_catalog, public AS $$
 SELECT p_rule.calendar_system='gregorian' AND p_day >= p_rule.start_date
 AND (p_rule.until_date IS NULL OR p_day <= p_rule.until_date)
 AND CASE p_rule.frequency
 WHEN 'once' THEN p_day=p_rule.start_date
 WHEN 'daily' THEN (p_day-p_rule.start_date) % p_rule.interval_count=0
 WHEN 'weekly' THEN extract(isodow FROM p_day)::smallint=ANY(p_rule.weekdays)
   AND ((date_trunc('week',p_day::timestamp)::date-
         date_trunc('week',p_rule.start_date::timestamp)::date)/7) % p_rule.interval_count=0
 WHEN 'monthly' THEN extract(day FROM p_day)::smallint=ANY(p_rule.month_days)
   AND ((extract(year FROM p_day)::int-extract(year FROM p_rule.start_date)::int)*12
       +extract(month FROM p_day)::int-extract(month FROM p_rule.start_date)::int) % p_rule.interval_count=0
 WHEN 'yearly' THEN extract(month FROM p_day)::smallint=ANY(p_rule.months)
   AND extract(day FROM p_day)::smallint=ANY(p_rule.month_days)
   AND (extract(year FROM p_day)::int-extract(year FROM p_rule.start_date)::int) % p_rule.interval_count=0
 ELSE false END
$$;

CREATE OR REPLACE FUNCTION public.generate_event_occurrences(p_from_date date, p_to_date date)
RETURNS TABLE(event_id bigint,event_title text,occurrence_date date,start_time time,end_time time,timezone text)
LANGUAGE plpgsql STABLE SET search_path = pg_catalog, public AS $$
BEGIN
 IF p_from_date IS NULL OR p_to_date IS NULL OR NOT isfinite(p_from_date) OR NOT isfinite(p_to_date)
    OR p_to_date < p_from_date OR p_to_date-p_from_date > 3660 THEN
    RAISE EXCEPTION 'Occurrence window must be finite, ordered and at most 3660 days' USING ERRCODE='22023'; END IF;
 RETURN QUERY SELECT e.id, coalesce(x.title,e.title), d.day::date,
    coalesce(x.start_time,e.start_time), CASE WHEN x.event_id IS NOT NULL THEN x.end_time ELSE e.end_time END,
    e.timezone
 FROM public.schedule_events e JOIN public.recurrence_rules r ON r.event_id=e.id
 CROSS JOIN LATERAL generate_series(p_from_date::timestamp,p_to_date::timestamp,interval '1 day') d(day)
 LEFT JOIN public.schedule_occurrence_overrides x ON x.event_id=e.id AND x.occurrence_date=d.day::date
 WHERE e.enabled AND public.gregorian_rule_matches(r,d.day::date) AND NOT coalesce(x.cancelled,false)
 ORDER BY d.day,e.start_time,e.id;
END $$;

CREATE FUNCTION public.gregorian_snapshot(p_event_id bigint) RETURNS jsonb
LANGUAGE sql STABLE SET search_path = pg_catalog, public AS $$
 SELECT jsonb_build_object('event',to_jsonb(e),'rule',to_jsonb(r),'overrides',
    coalesce((SELECT jsonb_agg(to_jsonb(x) ORDER BY x.occurrence_date)
      FROM public.schedule_occurrence_overrides x WHERE x.event_id=e.id),'[]'::jsonb))
 FROM public.schedule_events e JOIN public.recurrence_rules r ON r.event_id=e.id WHERE e.id=p_event_id
$$;

CREATE FUNCTION public.propose_gregorian_change(p_action text,p_scope text,p_event_id bigint,
 p_occurrence_date date,p_data jsonb,p_user_id bigint) RETURNS bigint
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE original jsonb; request_id bigint; validation_data jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 IF p_user_id IS NULL OR p_action IS NULL OR p_action NOT IN ('add','update','remove')
    OR p_scope IS NULL OR p_scope NOT IN ('series','occurrence') THEN
    RAISE EXCEPTION 'Invalid proposal action, scope or requester' USING ERRCODE='22023'; END IF;
 IF (p_action='add' AND (p_scope<>'series' OR p_event_id IS NOT NULL)) OR
    (p_scope='series' AND p_occurrence_date IS NOT NULL) OR
    (p_scope='occurrence' AND p_occurrence_date IS NULL) THEN
    RAISE EXCEPTION 'Invalid scope identity' USING ERRCODE='22023'; END IF;
 IF p_action<>'add' THEN
    PERFORM FROM public.schedule_events e WHERE e.id=p_event_id AND e.enabled FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Activity unavailable' USING ERRCODE='22023'; END IF;
    original := public.gregorian_snapshot(p_event_id);
    IF original IS NULL OR original->'rule'->>'calendar_system'<>'gregorian' THEN
        RAISE EXCEPTION 'Gregorian rule required' USING ERRCODE='22023'; END IF;
    IF p_scope='occurrence' AND NOT EXISTS (SELECT FROM public.generate_event_occurrences(
       p_occurrence_date,p_occurrence_date) o WHERE o.event_id=p_event_id) THEN
       RAISE EXCEPTION 'Occurrence unavailable' USING ERRCODE='22023'; END IF;
 END IF;
 IF p_action<>'remove' THEN
    validation_data := p_data;
    IF p_scope='occurrence' THEN
        IF p_data ? 'recurrence_rule' THEN RAISE EXCEPTION 'Occurrence cannot change recurrence' USING ERRCODE='22023'; END IF;
        validation_data := p_data || jsonb_build_object('recurrence_rule',
          (original->'rule') - ARRAY['id','event_id','hindu_rule','rule_options','created_at','updated_at']);
    END IF;
    PERFORM public.gregorian_validate(validation_data);
 END IF;
 INSERT INTO public.schedule_change_requests(action,event_id,requested_by,proposed_data)
 VALUES(p_action,p_event_id,p_user_id,jsonb_build_object('api_version',2,'scope',p_scope,
        'occurrence_date',p_occurrence_date,'desired',p_data,'original',original)) RETURNING id INTO request_id;
 RETURN request_id;
END $$;

CREATE FUNCTION public.decide_gregorian_change(p_request_id bigint,p_user_id bigint,p_decision text,
 p_force boolean DEFAULT false,p_horizon_days integer DEFAULT 730) RETURNS TABLE(success boolean,message text)
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE req public.schedule_change_requests%ROWTYPE; data jsonb; rule jsonb; ev bigint;
 scope text; day date; start_day date; end_day date; conflicts integer; original jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 IF p_decision IS NULL OR p_decision NOT IN ('approve','reject') OR p_horizon_days IS NULL
    OR p_horizon_days NOT BETWEEN 1 AND 3660 THEN
    RETURN QUERY SELECT false,'Invalid decision or conflict horizon'; RETURN; END IF;
 SELECT * INTO req FROM public.schedule_change_requests q
 WHERE q.id=p_request_id AND q.requested_by=p_user_id FOR UPDATE;
 IF NOT FOUND OR req.status<>'pending' OR req.proposed_data->>'api_version' IS DISTINCT FROM '2' THEN
    RETURN QUERY SELECT false,'Request unavailable, unauthorized or already decided'; RETURN; END IF;
 IF p_decision='reject' THEN
    UPDATE public.schedule_change_requests SET status='rejected',decided_at=now() WHERE id=req.id;
    RETURN QUERY SELECT true,'Rejected; schedule unchanged'; RETURN;
 END IF;
 data:=req.proposed_data->'desired'; scope:=req.proposed_data->>'scope';
 day:=(req.proposed_data->>'occurrence_date')::date; ev:=req.event_id;
 IF req.action<>'add' THEN
    PERFORM FROM public.schedule_events e WHERE e.id=ev AND e.enabled FOR UPDATE;
    IF NOT FOUND OR public.gregorian_snapshot(ev) IS DISTINCT FROM req.proposed_data->'original' THEN
       RETURN QUERY SELECT false,'Activity changed; create a new proposal'; RETURN; END IF;
 END IF;
 -- Changes and conflict checks share a subtransaction: a blocked approval leaves no writes.
 BEGIN
 IF req.action='remove' AND scope='series' THEN
    UPDATE public.schedule_events SET enabled=false,updated_at=now() WHERE id=ev;
 ELSIF scope='occurrence' THEN
    INSERT INTO public.schedule_occurrence_overrides(event_id,occurrence_date,cancelled,title,start_time,end_time)
    VALUES(ev,day,req.action='remove',data->>'title',(data->>'start_time')::time,(data->>'end_time')::time)
    ON CONFLICT(event_id,occurrence_date) DO UPDATE SET cancelled=excluded.cancelled,title=excluded.title,
       start_time=excluded.start_time,end_time=excluded.end_time;
 ELSE
    PERFORM public.gregorian_validate(data); rule:=data->'recurrence_rule';
    IF req.action='add' THEN
      INSERT INTO public.schedule_events(title,start_time,end_time,timezone,recurrence,event_date)
      VALUES(data->>'title',(data->>'start_time')::time,(data->>'end_time')::time,'Asia/Kolkata',
             'once',(rule->>'start_date')::date) RETURNING id INTO ev;
    ELSE
      UPDATE public.schedule_events SET title=data->>'title',start_time=(data->>'start_time')::time,
             end_time=(data->>'end_time')::time,updated_at=now() WHERE id=ev;
    END IF;
    INSERT INTO public.recurrence_rules(event_id,calendar_system,frequency,interval_count,start_date,
        until_date,weekdays,month_days,months,rule_options)
    VALUES(ev,'gregorian',rule->>'frequency',(rule->>'interval_count')::int,(rule->>'start_date')::date,
        (rule->>'until_date')::date,
        ARRAY(SELECT value::smallint FROM jsonb_array_elements_text(coalesce(rule->'weekdays','[]'))),
        ARRAY(SELECT value::smallint FROM jsonb_array_elements_text(coalesce(rule->'month_days','[]'))),
        ARRAY(SELECT value::smallint FROM jsonb_array_elements_text(coalesce(rule->'months','[]'))),
        '{"managed_by":"m2d"}')
    ON CONFLICT(event_id) DO UPDATE SET frequency=excluded.frequency,interval_count=excluded.interval_count,
       start_date=excluded.start_date,until_date=excluded.until_date,weekdays=excluded.weekdays,
       month_days=excluded.month_days,months=excluded.months,rule_options=excluded.rule_options,updated_at=now();
 END IF;
 IF req.action<>'remove' THEN
    start_day:=CASE WHEN scope='occurrence' THEN day ELSE
       greatest((now() AT TIME ZONE 'Asia/Kolkata')::date,(data->'recurrence_rule'->>'start_date')::date) END;
    end_day:=CASE WHEN scope='occurrence' THEN day ELSE start_day+p_horizon_days END;
    SELECT count(*) INTO conflicts FROM public.generate_event_occurrences(start_day,end_day) a
    JOIN public.generate_event_occurrences(start_day,end_day) b ON a.occurrence_date=b.occurrence_date
    WHERE a.event_id=ev AND b.event_id<>ev
      AND ( (a.end_time IS NOT NULL AND b.end_time IS NOT NULL AND a.start_time<b.end_time AND b.start_time<a.end_time)
         OR (a.end_time IS NULL AND b.end_time IS NOT NULL AND a.start_time>=b.start_time AND a.start_time<b.end_time)
         OR (a.end_time IS NOT NULL AND b.end_time IS NULL AND b.start_time>=a.start_time AND b.start_time<a.end_time)
         OR (a.end_time IS NULL AND b.end_time IS NULL AND a.start_time=b.start_time));
    IF conflicts>0 AND NOT coalesce(p_force,false) THEN
       RAISE EXCEPTION 'Occurrence conflicts in reviewed horizon' USING ERRCODE='P2001'; END IF;
 END IF;
 UPDATE public.schedule_change_requests SET status='approved',event_id=ev,decided_at=now() WHERE id=req.id;
 EXCEPTION WHEN SQLSTATE 'P2001' THEN
    RETURN QUERY SELECT false,'Conflicts found; approval requires explicit force'; RETURN;
 END;
 RETURN QUERY SELECT true,format('Approved; conflicts checked within %s days',p_horizon_days);
END $$;

CREATE OR REPLACE FUNCTION public.dispatch_schedule_decision(p_request_id bigint,p_user_id bigint,
 p_decision text,p_force boolean DEFAULT false) RETURNS TABLE(success boolean,message text)
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE req public.schedule_change_requests%ROWTYPE;
BEGIN
 SELECT * INTO req FROM public.schedule_change_requests q WHERE q.id=p_request_id AND q.requested_by=p_user_id;
 IF req.proposed_data->>'api_version'='2' THEN
    RETURN QUERY SELECT * FROM public.decide_gregorian_change(p_request_id,p_user_id,p_decision,p_force);
 ELSIF p_decision='approve' AND req.action='add' AND req.proposed_data ? 'recurrence_rule' THEN
    RETURN QUERY SELECT * FROM public.approve_advanced_schedule_add(p_request_id,p_user_id,p_force);
 ELSE
    RETURN QUERY SELECT * FROM public.process_schedule_decision(p_request_id,p_user_id,p_decision,p_force);
 END IF;
END $$;
