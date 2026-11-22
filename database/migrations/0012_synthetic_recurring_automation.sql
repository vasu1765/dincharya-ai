DO $$ BEGIN
 IF current_database()<>'dincharya_app_test' OR session_user<>'synthetic_test' THEN
  RAISE EXCEPTION 'Isolated synthetic setup required';
 END IF;
END $$;
CREATE TABLE lunar_private.recurring_control (
 id uuid PRIMARY KEY,
 owner_subject bigint NOT NULL,
 series_id uuid UNIQUE REFERENCES lunar_private.series,
 event_id bigint UNIQUE REFERENCES public.schedule_events,
 mode text NOT NULL CHECK(mode IN ('automatic','manual')),
 offsets integer[] NOT NULL CHECK(lunar_private.valid_offsets(offsets)),
 revision integer NOT NULL DEFAULT 1 CHECK(revision>0),
 state text NOT NULL DEFAULT 'active' CHECK(state IN ('active','paused','cancelled')),
 CHECK(num_nonnulls(series_id,event_id)=1)
);
CREATE TABLE lunar_private.recurring_audit (
 action uuid PRIMARY KEY,
 control uuid NOT NULL REFERENCES lunar_private.recurring_control,
 request jsonb NOT NULL,
 snapshot jsonb NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TRIGGER recurring_audit_immutable BEFORE UPDATE OR DELETE ON lunar_private.recurring_audit
 FOR EACH ROW EXECUTE FUNCTION lunar_private.immutable();
CREATE TABLE lunar_private.projection_review (
 control uuid NOT NULL REFERENCES lunar_private.recurring_control,
 target_year integer NOT NULL CHECK(target_year BETWEEN 2000 AND 2099),
 revision integer NOT NULL,
 reason text NOT NULL CHECK(length(reason) BETWEEN 1 AND 100),
 alert_reserved_at timestamptz,
 PRIMARY KEY(control,target_year,revision)
);
GRANT SELECT,INSERT,UPDATE ON lunar_private.recurring_control TO dincharya_lunar_executor;
GRANT SELECT,INSERT ON lunar_private.recurring_audit,lunar_private.projection_review TO dincharya_lunar_executor;
GRANT UPDATE(alert_reserved_at) ON lunar_private.projection_review TO dincharya_lunar_executor;

CREATE FUNCTION lunar_api.approve_recurring(
 p_action uuid,p_mode text,p_offsets integer[],p_spec jsonb,p_expires timestamptz
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE subject bigint; snapshot jsonb; req bigint; event bigint; series uuid; result jsonb; audited record;
 command jsonb:=jsonb_build_object('mode',p_mode,'offsets',p_offsets,'spec',p_spec);
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 subject:=lunar_private.principal('owner');
 IF p_action IS NULL OR p_mode IS NULL OR p_mode NOT IN ('automatic','manual')
 OR NOT lunar_private.valid_offsets(p_offsets) OR p_expires IS NULL OR NOT isfinite(p_expires)
 OR p_expires<=clock_timestamp() OR p_expires>clock_timestamp()+interval '30 minutes'
 OR jsonb_typeof(p_spec) IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'Invalid recurring approval'; END IF;
 SELECT a.request,a.snapshot INTO audited FROM lunar_private.recurring_audit a
 JOIN lunar_private.recurring_control c ON c.id=a.control WHERE a.action=p_action AND c.owner_subject=subject;
 IF FOUND THEN
  IF audited.request IS DISTINCT FROM command THEN RAISE EXCEPTION 'Approval changed'; END IF;
  RETURN audited.snapshot;
 END IF;
 IF (SELECT count(*) FROM lunar_private.recurring_control WHERE owner_subject=subject)>=64 THEN
  RAISE EXCEPTION 'Development rule limit reached'; END IF;
 IF p_spec->>'kind'='lunar' THEN
  series:=(p_spec->>'series')::uuid;
  SELECT to_jsonb(c) INTO snapshot FROM lunar_private.recurring_control c
  WHERE c.series_id=series AND c.owner_subject=subject;
  IF FOUND THEN RAISE EXCEPTION 'Use the existing recurring control'; END IF;
  result:=lunar_api.approve_annual_rule(series,p_action,p_action,p_spec->>'purpose',p_spec->'rule',
       (p_spec->>'year')::int,p_spec->>'title',(p_spec->>'time')::time,p_expires);
  IF result->>'status'<>'approved' THEN RAISE EXCEPTION 'Annual rule approval refused'; END IF;
 ELSIF p_spec->>'kind'='gregorian' AND p_mode='automatic' THEN
  req:=public.propose_gregorian_change('add','series',NULL,NULL,p_spec->'desired',subject);
  IF NOT (SELECT success FROM public.decide_gregorian_change(req,subject,'approve',false,730)) THEN
   RAISE EXCEPTION 'Gregorian approval refused';
  END IF;
  SELECT event_id INTO event FROM public.schedule_change_requests WHERE id=req;
  PERFORM lunar_private.set_notification_policy(event,p_offsets);
 ELSE RAISE EXCEPTION 'Unsupported recurrence mode'; END IF;
 INSERT INTO lunar_private.recurring_control(id,owner_subject,series_id,event_id,mode,offsets)
 VALUES(p_action,subject,series,event,p_mode,p_offsets) RETURNING to_jsonb(recurring_control) INTO snapshot;
 snapshot:=snapshot-'owner_subject';
 INSERT INTO lunar_private.recurring_audit(action,control,request,snapshot) VALUES(p_action,p_action,command,snapshot);
 RETURN snapshot;
END $$;

CREATE FUNCTION lunar_api.recurring_controls() RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE subject bigint:=lunar_private.principal('owner');
BEGIN
 RETURN jsonb_build_object(
  'controls',(SELECT coalesce(jsonb_agg(c ORDER BY c.id),'[]') FROM (
    SELECT c.id,c.series_id,c.event_id,c.mode,c.offsets,c.revision,c.state,
           coalesce(a.title,e.title) AS title,
           coalesce((SELECT jsonb_agg(DISTINCT extract(year FROM calc.selection)::int)
             FROM lunar_private.occurrences o JOIN lunar_private.calculations calc ON calc.id=o.calculation_id
             WHERE o.series_id=c.series_id AND calc.selection IS NOT NULL
               AND (o.cancelled OR o.event_id IS NOT NULL)),'[]') AS closed_years
    FROM lunar_private.recurring_control c LEFT JOIN lunar_private.annual_rules a ON a.series_id=c.series_id
    LEFT JOIN public.schedule_events e ON e.id=c.event_id
    WHERE c.owner_subject=subject ORDER BY c.id LIMIT 64) c),
  'withheld',(SELECT coalesce(jsonb_agg(r),'[]') FROM (
    SELECT p.control,p.target_year,p.reason FROM lunar_private.projection_review p
    JOIN lunar_private.recurring_control c ON c.id=p.control AND c.revision=p.revision
    WHERE c.owner_subject=subject AND c.state='active'
    AND p.target_year>=extract(year FROM clock_timestamp() AT TIME ZONE 'Asia/Kolkata')::int
    ORDER BY p.target_year,p.control) r));
END $$;

CREATE FUNCTION lunar_api.recurring_withhold(p_control uuid,p_revision integer,p_year integer,p_reason text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 IF NOT EXISTS(SELECT FROM lunar_private.recurring_control c WHERE c.id=p_control
 AND c.owner_subject=lunar_private.principal('owner') AND c.revision=p_revision
 AND c.state='active' AND c.mode='automatic' AND c.series_id IS NOT NULL) THEN
  RAISE EXCEPTION 'Projection revision changed';
 END IF;
 INSERT INTO lunar_private.projection_review(control,target_year,revision,reason)
 VALUES(p_control,p_year,p_revision,p_reason) ON CONFLICT DO NOTHING;
END $$;

CREATE FUNCTION lunar_api.reserve_recurring_alert() RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE result jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 WITH next_alert AS (
  SELECT r.control,r.target_year,r.revision,c0.title
  FROM lunar_private.projection_review r JOIN lunar_private.recurring_control c USING (revision)
  JOIN lunar_private.annual_rules c0 ON c0.series_id=c.series_id
  WHERE c.id=r.control AND c.owner_subject=lunar_private.principal('owner') AND c.state='active'
    AND r.alert_reserved_at IS NULL
    AND r.target_year>=extract(year FROM clock_timestamp() AT TIME ZONE 'Asia/Kolkata')::int
  ORDER BY r.target_year,r.control LIMIT 1
 )
 UPDATE lunar_private.projection_review r SET alert_reserved_at=clock_timestamp()
 FROM next_alert n WHERE (r.control,r.target_year,r.revision)=(n.control,n.target_year,n.revision)
 RETURNING jsonb_build_object('title',n.title,'year',r.target_year,'reason',r.reason) INTO result;
 RETURN result;
END $$;

-- The separate calculator records only evidence. The owner service then atomically
-- binds the checked revision, native appointment and notification policy.
CREATE FUNCTION lunar_api.project_recurring(
 p_control uuid,p_revision integer,p_occurrence uuid,p_action uuid,p_decision uuid,p_observation bigint
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE c lunar_private.recurring_control%ROWTYPE; a lunar_private.annual_rules%ROWTYPE;
 o lunar_private.occurrences%ROWTYPE; calc lunar_private.calculations%ROWTYPE;
 day date; req bigint; result jsonb; subject bigint;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 subject:=lunar_private.principal('owner');
 SELECT * INTO c FROM lunar_private.recurring_control WHERE id=p_control AND owner_subject=subject
  AND revision=p_revision AND state='active' AND mode='automatic' AND series_id IS NOT NULL;
 IF NOT FOUND THEN RAISE EXCEPTION 'Projection approval changed'; END IF;
 SELECT * INTO a FROM lunar_private.annual_rules WHERE series_id=c.series_id;
 SELECT * INTO o FROM lunar_private.occurrences WHERE id=p_occurrence AND series_id=c.series_id
  AND observation=p_observation AND NOT cancelled;
 IF NOT FOUND THEN RAISE EXCEPTION 'Projection unavailable'; END IF;
 IF o.event_id IS NOT NULL THEN RETURN jsonb_build_object('status','already_scheduled','event_id',o.event_id); END IF;
 SELECT * INTO calc FROM lunar_private.calculations WHERE id=o.calculation_id;
 day:=calc.selection;
 IF day IS NULL OR extract(year FROM day)<a.start_year OR
   (day+a.appointment_time) AT TIME ZONE 'Asia/Kolkata'<=clock_timestamp() OR
   day>(clock_timestamp() AT TIME ZONE 'Asia/Kolkata')::date+400 THEN
  RAISE EXCEPTION 'Outside the rolling projection window';
 END IF;
 req:=lunar_api.propose_occurrence(p_action,p_occurrence,'select',calc.series_revision,o.revision,o.observation,
    jsonb_build_object('date',day,'title',a.title,'start_time',to_char(a.appointment_time,'HH24:MI')));
 result:=lunar_api.decide(p_decision,req,'approve',lunar_api.inspect_request(req)->>'fingerprint',true,false);
 IF result->>'status'='approved' THEN
  PERFORM lunar_private.set_notification_policy((result->>'event_id')::bigint,c.offsets);
 END IF;
 RETURN result;
END $$;

-- Reviewed changes use the current revision; the existing projections remain
-- immutable except for their future enabled state and notification preferences.
CREATE FUNCTION lunar_api.change_recurring(
 p_control uuid,p_revision integer,p_action uuid,p_operation text,p_offsets integer[],p_expires timestamptz
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE c lunar_private.recurring_control%ROWTYPE; subject bigint; member record; snap jsonb;
 req bigint; result jsonb; previous record;
 today date:=(clock_timestamp() AT TIME ZONE 'Asia/Kolkata')::date;
 command jsonb:=jsonb_build_object('operation',p_operation,'offsets',p_offsets);
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 subject:=lunar_private.principal('owner');
 IF p_expires IS NULL OR NOT isfinite(p_expires) OR p_expires<=clock_timestamp()
 OR p_expires>clock_timestamp()+interval '30 minutes' THEN RAISE EXCEPTION 'Review expired'; END IF;
 SELECT a.request,a.snapshot INTO previous FROM lunar_private.recurring_audit a
 JOIN lunar_private.recurring_control c0 ON c0.id=a.control
 WHERE a.action=p_action AND a.control=p_control AND c0.owner_subject=subject;
 IF FOUND THEN
  IF previous.request IS DISTINCT FROM command THEN RAISE EXCEPTION 'Review changed'; END IF;
  RETURN previous.snapshot;
 END IF;
 SELECT * INTO c FROM lunar_private.recurring_control WHERE id=p_control AND owner_subject=subject
  AND revision=p_revision AND state<>'cancelled';
 IF NOT FOUND OR p_operation IS NULL OR p_operation NOT IN ('pause','resume','cancel','notifications','automatic','manual')
 OR (p_operation IN ('automatic','manual') AND c.series_id IS NULL)
 OR (p_operation='notifications' AND NOT lunar_private.valid_offsets(p_offsets)) THEN
  RAISE EXCEPTION 'Recurring review is unavailable';
 END IF;
 IF p_operation='cancel' AND c.series_id IS NOT NULL THEN
  snap:=lunar_api.inspect_series(c.series_id);
  req:=lunar_api.propose_series_cancel(p_action,c.series_id,(snap->'series'->>'revision')::int,snap->'manifest');
  result:=lunar_api.decide(p_action,req,'approve',lunar_api.inspect_request(req)->>'fingerprint',true,false);
  IF result->>'status'<>'approved' THEN RAISE EXCEPTION 'Cancellation refused'; END IF;
 END IF;
 FOR member IN
  SELECT e.id FROM public.schedule_events e LEFT JOIN lunar_private.occurrences o ON o.event_id=e.id
   WHERE e.id=c.event_id OR (o.series_id=c.series_id AND NOT o.cancelled
   AND (e.event_date+e.start_time) AT TIME ZONE e.timezone>clock_timestamp())
 LOOP
  IF p_operation='notifications' THEN
   PERFORM lunar_private.set_notification_policy(member.id,p_offsets);
  ELSIF p_operation IN ('pause','resume','cancel') THEN
   UPDATE public.schedule_events SET enabled=(p_operation='resume') WHERE id=member.id;
   IF p_operation='resume' AND EXISTS (
     WITH upcoming AS MATERIALIZED (SELECT * FROM public.generate_event_occurrences(today,today+400))
     SELECT FROM upcoming a JOIN upcoming b USING(occurrence_date)
     WHERE a.event_id=member.id AND b.event_id<>member.id
     AND ((a.occurrence_date+a.start_time) AT TIME ZONE a.timezone)>clock_timestamp()
     AND ((a.end_time IS NOT NULL AND b.end_time IS NOT NULL AND a.start_time<b.end_time AND b.start_time<a.end_time)
       OR (a.end_time IS NULL AND b.end_time IS NOT NULL AND a.start_time>=b.start_time AND a.start_time<b.end_time)
       OR (a.end_time IS NOT NULL AND b.end_time IS NULL AND b.start_time>=a.start_time AND b.start_time<a.end_time)
       OR (a.end_time IS NULL AND b.end_time IS NULL AND a.start_time=b.start_time))) THEN
    RAISE EXCEPTION 'Resuming the rule would create a schedule conflict';
   END IF;
  END IF;
 END LOOP;
 UPDATE lunar_private.recurring_control SET revision=revision+1,
  offsets=CASE WHEN p_operation='notifications' THEN p_offsets ELSE offsets END,
  mode=CASE WHEN p_operation IN ('automatic','manual') THEN p_operation ELSE mode END,
  state=CASE p_operation WHEN 'pause' THEN 'paused' WHEN 'resume' THEN 'active'
             WHEN 'cancel' THEN 'cancelled' ELSE state END
 WHERE id=p_control RETURNING to_jsonb(recurring_control)-'owner_subject' INTO snap;
 INSERT INTO lunar_private.recurring_audit(action,control,request,snapshot) VALUES(p_action,p_control,command,snap);
 RETURN snap;
END $$;

DO $$ DECLARE signature regprocedure; BEGIN
 FOR signature IN SELECT p.oid::regprocedure FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
  WHERE n.nspname='lunar_api' AND p.proname IN ('approve_recurring','recurring_controls',
    'recurring_withhold','reserve_recurring_alert','project_recurring','change_recurring')
 LOOP
  EXECUTE format('ALTER FUNCTION %s OWNER TO dincharya_lunar_executor',signature);
  EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC',signature);
  EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO dincharya_lunar_owner',signature);
 END LOOP;
END $$;

CREATE FUNCTION lunar_api.decide_recurring_manual(
 p_control uuid,p_revision integer,p_action uuid,p_request bigint,p_choice text,p_hash text,p_expires timestamptz
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE c lunar_private.recurring_control%ROWTYPE; result jsonb; proposal jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 SELECT * INTO c FROM lunar_private.recurring_control WHERE id=p_control AND revision=p_revision
  AND owner_subject=lunar_private.principal('owner') AND mode='manual' AND state='active';
 IF NOT FOUND THEN RAISE EXCEPTION 'Manual rule changed'; END IF;
 proposal:=lunar_api.inspect_request(p_request)->'proposal';
 IF (proposal->>'series')::uuid IS DISTINCT FROM c.series_id OR proposal->>'operation'<>'select' THEN
  RAISE EXCEPTION 'Manual appointment unavailable';
 END IF;
 result:=lunar_api.decide_annual_review(p_action,p_request,p_choice,p_hash,p_expires);
 IF result->>'status'='approved' THEN
  PERFORM lunar_private.set_notification_policy((result->>'event_id')::bigint,c.offsets);
 END IF;
 RETURN result;
END $$;
ALTER FUNCTION lunar_api.decide_recurring_manual(uuid,integer,uuid,bigint,text,text,timestamptz)
 OWNER TO dincharya_lunar_executor;
REVOKE ALL ON FUNCTION lunar_api.decide_recurring_manual(uuid,integer,uuid,bigint,text,text,timestamptz) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION lunar_api.decide_recurring_manual(uuid,integer,uuid,bigint,text,text,timestamptz) TO dincharya_lunar_owner;

CREATE FUNCTION lunar_api.recurring_fingerprint(p_control uuid) RETURNS text
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT lunar_private.hash(jsonb_build_object('control',to_jsonb(c),
   'series',CASE WHEN c.series_id IS NOT NULL THEN lunar_api.inspect_series(c.series_id) END,
   'event',CASE WHEN c.event_id IS NOT NULL THEN public.gregorian_snapshot(c.event_id) END))
 FROM lunar_private.recurring_control c WHERE c.id=p_control AND c.owner_subject=lunar_private.principal('owner')
$$;
ALTER FUNCTION lunar_api.recurring_fingerprint(uuid) OWNER TO dincharya_lunar_executor;
REVOKE ALL ON FUNCTION lunar_api.recurring_fingerprint(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION lunar_api.recurring_fingerprint(uuid) TO dincharya_lunar_owner;

CREATE FUNCTION lunar_api.reviewed_recurring_change(
 p_control uuid,p_revision integer,p_action uuid,p_operation text,p_offsets integer[],p_hash text,
 p_spec jsonb,p_expires timestamptz
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE c lunar_private.recurring_control%ROWTYPE; previous record; snap jsonb; req bigint;
 command jsonb:=jsonb_build_object('operation',p_operation,'offsets',p_offsets,'spec',p_spec,'fingerprint',p_hash);
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 IF p_expires IS NULL OR p_expires<=clock_timestamp() OR p_expires>clock_timestamp()+interval '30 minutes' THEN
  RAISE EXCEPTION 'Reviewed change expired'; END IF;
 SELECT * INTO c FROM lunar_private.recurring_control WHERE id=p_control AND owner_subject=lunar_private.principal('owner');
 IF NOT FOUND THEN RAISE EXCEPTION 'Review unavailable'; END IF;
 SELECT request,snapshot INTO previous FROM lunar_private.recurring_audit WHERE action=p_action AND control=p_control;
 IF FOUND THEN
  IF previous.request IS DISTINCT FROM command THEN RAISE EXCEPTION 'Reviewed change differs'; END IF;
  RETURN previous.snapshot;
 END IF;
 IF p_hash IS NULL OR p_hash IS DISTINCT FROM lunar_api.recurring_fingerprint(p_control) OR c.revision<>p_revision THEN
  RAISE EXCEPTION 'Reviewed schedule changed'; END IF;
 IF p_operation='replace' THEN
  IF c.state<>'active' OR p_spec->>'kind' IS DISTINCT FROM
      (CASE WHEN c.series_id IS NULL THEN 'gregorian' ELSE 'lunar' END) THEN
   RAISE EXCEPTION 'Calendar conversion requires a separate rule'; END IF;
  IF c.event_id IS NOT NULL THEN
   -- Keep the event ID, notification slot identities and occurrence overrides.
   req:=public.propose_gregorian_change('update','series',c.event_id,NULL,p_spec->'desired',c.owner_subject);
   IF NOT (SELECT success FROM public.decide_gregorian_change(req,c.owner_subject,'approve',false,730)) THEN
    RAISE EXCEPTION 'Gregorian change refused';
   END IF;
   UPDATE lunar_private.notification_policy SET effective_at=clock_timestamp() WHERE event_id=c.event_id;
   UPDATE lunar_private.recurring_control SET revision=revision+1 WHERE id=c.id
    RETURNING to_jsonb(recurring_control)-'owner_subject' INTO snap;
  ELSE
   -- A replacement lunar series gets new occurrence identities. Withhold it
   -- when any future appointment has already reached a delivery boundary.
   IF EXISTS(SELECT FROM lunar_private.occurrences o JOIN public.schedule_events e ON e.id=o.event_id
     WHERE o.series_id=c.series_id AND (e.event_date+e.start_time) AT TIME ZONE e.timezone>clock_timestamp()
     AND (EXISTS(SELECT FROM lunar_private.notification_slot s WHERE s.event_id=e.id
                  AND s.status IN ('sent','uncertain','sending'))
       OR EXISTS(SELECT FROM public.reminder_deliveries d WHERE d.event_id=e.id
                  AND d.status IN ('sent','uncertain','sending')))) THEN
    RAISE EXCEPTION 'Future appointment already has delivery history';
   END IF;
   PERFORM lunar_api.change_recurring(p_control,p_revision,gen_random_uuid(),'cancel','{}',p_expires);
   snap:=lunar_api.approve_recurring(gen_random_uuid(),c.mode,c.offsets,p_spec,p_expires);
  END IF;
 ELSE
  snap:=lunar_api.change_recurring(p_control,p_revision,gen_random_uuid(),p_operation,p_offsets,p_expires);
 END IF;
 INSERT INTO lunar_private.recurring_audit(action,control,request,snapshot) VALUES(p_action,p_control,command,snap);
 RETURN snap;
END $$;
ALTER FUNCTION lunar_api.reviewed_recurring_change(uuid,integer,uuid,text,integer[],text,jsonb,timestamptz)
 OWNER TO dincharya_lunar_executor;
REVOKE ALL ON FUNCTION lunar_api.reviewed_recurring_change(uuid,integer,uuid,text,integer[],text,jsonb,timestamptz) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION lunar_api.reviewed_recurring_change(uuid,integer,uuid,text,integer[],text,jsonb,timestamptz) TO dincharya_lunar_owner;
REVOKE EXECUTE ON FUNCTION lunar_api.change_recurring(uuid,integer,uuid,text,integer[],timestamptz) FROM dincharya_lunar_owner;
