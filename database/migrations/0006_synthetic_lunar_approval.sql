-- Isolated synthetic integration ONLY. No production scheduling enablement.
DO $$ BEGIN
 IF current_database()<>'dincharya_app_test' OR session_user<>'synthetic_test' THEN
  RAISE EXCEPTION 'Isolated synthetic lunar setup required';
 END IF;
 IF EXISTS(SELECT FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
   WHERE n.nspname='public' AND p.prosecdef) THEN
  RAISE EXCEPTION 'Unreviewed public SECURITY DEFINER function';
 END IF;
 IF EXISTS(SELECT FROM pg_roles WHERE rolname IN
  ('dincharya_lunar_executor','dincharya_lunar_owner','dincharya_lunar_calculator')) THEN
  RAISE EXCEPTION 'Lunar roles already exist; explicit review required';
 END IF;
END $$;
CREATE ROLE dincharya_lunar_executor NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE dincharya_lunar_owner NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE dincharya_lunar_calculator NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE SCHEMA lunar_private;
CREATE SCHEMA lunar_api;
REVOKE ALL ON SCHEMA lunar_private,lunar_api FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

CREATE TABLE lunar_private.principals (
 role_oid oid PRIMARY KEY, role_name name NOT NULL UNIQUE, owner_subject bigint NOT NULL,
 kind text NOT NULL CHECK(kind IN ('owner','calculator')), enabled boolean NOT NULL DEFAULT false
);
CREATE TABLE lunar_private.profiles (
 digest text PRIMARY KEY CHECK(digest ~ '^[0-9a-f]{64}$'),
 specification jsonb NOT NULL CHECK(jsonb_typeof(specification)='object'),
 enabled boolean NOT NULL DEFAULT false,
 environment text NOT NULL DEFAULT 'isolated_synthetic' CHECK(environment='isolated_synthetic'),
 CHECK(digest=pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(specification::text,'UTF8')),'hex'))
);
CREATE TABLE lunar_private.series (
 id uuid PRIMARY KEY, owner_subject bigint NOT NULL,
 purpose text NOT NULL CHECK(purpose IN ('birthday','wedding_anniversary','monthly')),
 rule jsonb, revision bigint NOT NULL DEFAULT 0 CHECK(revision>=0),
 enabled boolean NOT NULL DEFAULT true
);
CREATE TABLE lunar_private.occurrences (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), series_id uuid NOT NULL REFERENCES lunar_private.series,
 convention text NOT NULL CHECK(convention IN ('amanta','purnimanta')),
 month text NOT NULL CHECK(month IN ('chaitra','vaishakha','jyeshtha','ashadha','shravana','bhadrapada',
  'ashvina','kartika','margashirsha','pausha','magha','phalguna')),
 intercalation text NOT NULL CHECK(intercalation IN ('ordinary','adhika')),
 lunation_cycle integer NOT NULL CHECK(lunation_cycle BETWEEN -1300 AND 1300),
 paksha text NOT NULL CHECK(paksha IN ('shukla','krishna')),
 tithi smallint NOT NULL CHECK(tithi BETWEEN 1 AND 15),
 observation bigint NOT NULL DEFAULT 0 CHECK(observation>=0), calculation_id uuid,
 revision bigint NOT NULL DEFAULT 0 CHECK(revision>=0), cancelled boolean NOT NULL DEFAULT false,
 event_id bigint UNIQUE REFERENCES public.schedule_events(id),
 UNIQUE(series_id,convention,month,intercalation,lunation_cycle,paksha,tithi)
);
CREATE TABLE lunar_private.calculations (
 id uuid PRIMARY KEY, producer oid NOT NULL, producer_name name NOT NULL DEFAULT session_user, command jsonb NOT NULL,
 occurrence_id uuid NOT NULL REFERENCES lunar_private.occurrences,
 series_revision bigint NOT NULL, profile text NOT NULL REFERENCES lunar_private.profiles,
 evidence jsonb NOT NULL, selection date,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(selection IS NULL OR (isfinite(selection) AND selection BETWEEN date '1900-01-01' AND date '2100-12-31'))
);
ALTER TABLE lunar_private.occurrences ADD FOREIGN KEY(calculation_id) REFERENCES lunar_private.calculations;
-- Immutable approved snapshots and replay results share one append-only table.
CREATE TABLE lunar_private.actions (
 id uuid PRIMARY KEY, principal oid NOT NULL, principal_name name NOT NULL DEFAULT session_user,
 owner_subject bigint NOT NULL, request_id bigint NOT NULL REFERENCES public.schedule_change_requests,
 command jsonb NOT NULL, result jsonb NOT NULL, snapshot jsonb NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX lunar_one_final_decision ON lunar_private.actions(request_id)
 WHERE result->>'status' IN ('approved','rejected');

CREATE FUNCTION lunar_private.immutable() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$ BEGIN
 RAISE EXCEPTION 'Lunar evidence is immutable' USING ERRCODE='55000';
END $$;
CREATE TRIGGER lunar_calculation_immutable BEFORE UPDATE OR DELETE ON lunar_private.calculations
 FOR EACH ROW EXECUTE FUNCTION lunar_private.immutable();
CREATE TRIGGER lunar_calculation_no_truncate BEFORE TRUNCATE ON lunar_private.calculations
 FOR EACH STATEMENT EXECUTE FUNCTION lunar_private.immutable();
CREATE TRIGGER lunar_action_immutable BEFORE UPDATE OR DELETE ON lunar_private.actions
 FOR EACH ROW EXECUTE FUNCTION lunar_private.immutable();
CREATE TRIGGER lunar_action_no_truncate BEFORE TRUNCATE ON lunar_private.actions
 FOR EACH STATEMENT EXECUTE FUNCTION lunar_private.immutable();
CREATE TRIGGER lunar_profile_immutable BEFORE UPDATE OR DELETE ON lunar_private.profiles
 FOR EACH ROW EXECUTE FUNCTION lunar_private.immutable();
CREATE TRIGGER lunar_profile_no_truncate BEFORE TRUNCATE ON lunar_private.profiles
 FOR EACH STATEMENT EXECUTE FUNCTION lunar_private.immutable();

CREATE FUNCTION lunar_private.identity_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$ BEGIN
 IF TG_TABLE_NAME='series' THEN
  IF (NEW.id,NEW.owner_subject,NEW.purpose) IS DISTINCT FROM (OLD.id,OLD.owner_subject,OLD.purpose) THEN
   RAISE EXCEPTION 'Immutable series identity' USING ERRCODE='55000'; END IF;
 ELSE
  IF (NEW.id,NEW.series_id,NEW.convention,NEW.month,NEW.intercalation,NEW.lunation_cycle,NEW.paksha,NEW.tithi)
    IS DISTINCT FROM (OLD.id,OLD.series_id,OLD.convention,OLD.month,OLD.intercalation,OLD.lunation_cycle,OLD.paksha,OLD.tithi)
    OR (OLD.event_id IS NOT NULL AND NEW.event_id IS DISTINCT FROM OLD.event_id)
    OR (OLD.cancelled AND NOT NEW.cancelled) OR NEW.revision<OLD.revision OR NEW.observation<OLD.observation THEN
   RAISE EXCEPTION 'Immutable occurrence identity' USING ERRCODE='55000'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER lunar_series_identity BEFORE UPDATE ON lunar_private.series
 FOR EACH ROW EXECUTE FUNCTION lunar_private.identity_guard();
CREATE TRIGGER lunar_occurrence_identity BEFORE UPDATE ON lunar_private.occurrences
 FOR EACH ROW EXECUTE FUNCTION lunar_private.identity_guard();

CREATE FUNCTION lunar_private.authority_lock() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$ BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 IF TG_OP='DELETE' THEN RETURN OLD; ELSIF TG_OP='TRUNCATE' THEN RETURN NULL; ELSE RETURN NEW; END IF;
END $$;
CREATE TRIGGER lunar_authority_lock BEFORE INSERT OR UPDATE OR DELETE ON lunar_private.principals
 FOR EACH ROW EXECUTE FUNCTION lunar_private.authority_lock();
CREATE TRIGGER lunar_authority_truncate BEFORE TRUNCATE ON lunar_private.principals
 FOR EACH STATEMENT EXECUTE FUNCTION lunar_private.authority_lock();

CREATE FUNCTION lunar_private.principal(p_kind text) RETURNS bigint
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE subject bigint;
BEGIN
 IF current_database()<>'dincharya_app_test' THEN
  RAISE EXCEPTION 'Lunar API unavailable' USING ERRCODE='42501'; END IF;
 SELECT p.owner_subject INTO subject FROM lunar_private.principals p
 JOIN pg_catalog.pg_roles r ON r.oid=p.role_oid AND r.rolname=p.role_name
 WHERE r.rolname=session_user AND p.kind=p_kind AND p.enabled;
 IF NOT FOUND THEN RAISE EXCEPTION 'Lunar API unavailable' USING ERRCODE='42501'; END IF;
 RETURN subject;
END $$;
CREATE FUNCTION lunar_private.hash(p_value jsonb) RETURNS text
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT encode(sha256(convert_to(p_value::text,'UTF8')),'hex')
$$;
CREATE FUNCTION lunar_private.validate_rule(p_rule jsonb) RETURNS void
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$ BEGIN
 IF jsonb_typeof(p_rule) IS DISTINCT FROM 'object' OR
    NOT p_rule ?& ARRAY['convention','month','intercalation','paksha','tithi','repeated','birth_basis','profile'] OR
    EXISTS(SELECT FROM jsonb_object_keys(p_rule) k WHERE k NOT IN
      ('convention','month','intercalation','paksha','tithi','repeated','birth_basis','profile')) OR
    p_rule->>'convention' NOT IN ('amanta','purnimanta') OR
    p_rule->>'intercalation' NOT IN ('ordinary','adhika','both') OR
    p_rule->>'paksha' NOT IN ('shukla','krishna') OR
    p_rule->>'repeated' NOT IN ('first','last','review') OR
    p_rule->>'birth_basis' NOT IN ('explicit_rule','instant','sunrise') OR
    jsonb_typeof(p_rule->'tithi') IS DISTINCT FROM 'number' OR
    (p_rule->>'tithi') !~ '^(?:[1-9]|1[0-5])$' OR
    (p_rule->'month'<>'null'::jsonb AND p_rule->>'month' NOT IN
     ('chaitra','vaishakha','jyeshtha','ashadha','shravana','bhadrapada','ashvina','kartika',
      'margashirsha','pausha','magha','phalguna')) OR
    EXISTS(SELECT FROM jsonb_each(p_rule) kv WHERE kv.value='null'::jsonb AND kv.key<>'month') OR
    NOT EXISTS(SELECT FROM lunar_private.profiles p WHERE p.digest=p_rule->>'profile' AND p.enabled) THEN
  RAISE EXCEPTION 'Unsupported lunar rule' USING ERRCODE='22023'; END IF;
END $$;

-- This read-only boolean helper reveals no title, owner, date or snapshot. It
-- lets SECURITY INVOKER triggers test the real execution role, not a caller GUC.
CREATE FUNCTION public.lunar_projection_is_mapped(p_event bigint) RETURNS boolean
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET TimeZone='UTC' SET DateStyle='ISO,YMD' AS $$
 SELECT EXISTS(SELECT FROM lunar_private.occurrences o WHERE o.event_id=p_event)
$$;
CREATE FUNCTION public.guard_lunar_projection() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE target bigint; previous bigint; tagged boolean := false;
BEGIN
 IF TG_TABLE_NAME='schedule_change_requests' AND TG_OP<>'INSERT' THEN
  IF OLD.proposed_data->>'api_version'='lunar-1' THEN
   IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Immutable lunar request' USING ERRCODE='55000'; END IF;
   IF (NEW.id,NEW.action,NEW.requested_by,NEW.proposed_data) IS DISTINCT FROM
      (OLD.id,OLD.action,OLD.requested_by,OLD.proposed_data) OR
      (OLD.event_id IS NOT NULL AND NEW.event_id IS DISTINCT FROM OLD.event_id) OR
      (OLD.status<>'pending' AND (NEW.status,NEW.decided_at) IS DISTINCT FROM (OLD.status,OLD.decided_at)) THEN
    RAISE EXCEPTION 'Immutable lunar request snapshot' USING ERRCODE='55000'; END IF;
  END IF;
 END IF;
 IF current_user='dincharya_lunar_executor' THEN
  IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
 END IF;
 IF TG_TABLE_NAME='schedule_events' THEN
  IF TG_OP<>'INSERT' THEN target:=OLD.id; END IF;
 ELSE
  IF TG_OP<>'DELETE' THEN target:=NEW.event_id; END IF;
  IF TG_OP<>'INSERT' THEN previous:=OLD.event_id; END IF;
 END IF;
 IF TG_TABLE_NAME='schedule_change_requests' THEN
  IF TG_OP<>'DELETE' THEN tagged:=coalesce(NEW.proposed_data->>'api_version'='lunar-1',false); END IF;
  IF TG_OP<>'INSERT' THEN tagged:=tagged OR coalesce(OLD.proposed_data->>'api_version'='lunar-1',false); END IF;
 END IF;
 IF tagged OR public.lunar_projection_is_mapped(target) OR public.lunar_projection_is_mapped(previous) THEN
  RAISE EXCEPTION 'Mapped lunar activity requires lunar approval' USING ERRCODE='42501'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$;
CREATE TRIGGER guard_lunar_event BEFORE UPDATE OR DELETE ON public.schedule_events
 FOR EACH ROW EXECUTE FUNCTION public.guard_lunar_projection();
CREATE TRIGGER guard_lunar_rule BEFORE INSERT OR UPDATE OR DELETE ON public.recurrence_rules
 FOR EACH ROW EXECUTE FUNCTION public.guard_lunar_projection();
CREATE TRIGGER guard_lunar_override BEFORE INSERT OR UPDATE OR DELETE ON public.schedule_occurrence_overrides
 FOR EACH ROW EXECUTE FUNCTION public.guard_lunar_projection();
CREATE TRIGGER guard_lunar_request BEFORE INSERT OR UPDATE OR DELETE ON public.schedule_change_requests
 FOR EACH ROW EXECUTE FUNCTION public.guard_lunar_projection();

CREATE FUNCTION lunar_private.snapshot(p_series uuid,p_occurrence uuid) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT jsonb_build_object('series',to_jsonb(s),'occurrence',to_jsonb(o),
  'projection',public.gregorian_snapshot(o.event_id))
 FROM lunar_private.series s LEFT JOIN lunar_private.occurrences o ON o.id=p_occurrence AND o.series_id=s.id
 WHERE s.id=p_series
$$;
CREATE FUNCTION lunar_private.conflicts(p_data jsonb,p_event bigint) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $$
 -- Conservative reviewed set of ALL native occurrences on the selected date.
 -- The existing native decider alone determines temporal overlap.
 SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY x.event_id),'[]'::jsonb)
 FROM public.generate_event_occurrences((p_data->>'date')::date,(p_data->>'date')::date) x
 WHERE x.event_id IS DISTINCT FROM p_event
$$;
CREATE FUNCTION lunar_private.manifest(p_series uuid) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT coalesce(jsonb_agg(lunar_private.snapshot(p_series,o.id) ORDER BY o.id),'[]'::jsonb)
 FROM lunar_private.occurrences o WHERE o.series_id=p_series AND o.event_id IS NOT NULL AND NOT o.cancelled
$$;
CREATE FUNCTION lunar_private.review(p_request bigint) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT jsonb_build_object('request_id',q.id,'status',q.status,'proposal',q.proposed_data,
   'calculation',(SELECT to_jsonb(c) FROM lunar_private.calculations c WHERE c.id=(q.proposed_data->>'calculation')::uuid),
   'current',lunar_private.snapshot((q.proposed_data->>'series')::uuid,(q.proposed_data->>'occurrence')::uuid),
   'deliveries',coalesce((SELECT jsonb_agg(to_jsonb(d) ORDER BY d.id)
     FROM public.reminder_deliveries d WHERE d.event_id=q.event_id OR
       (q.proposed_data->>'operation'='cancel_series' AND EXISTS(SELECT FROM lunar_private.occurrences x
        WHERE x.series_id=(q.proposed_data->>'series')::uuid AND x.event_id=d.event_id))),'[]'::jsonb),
   'manifest',CASE WHEN q.proposed_data->>'operation'='cancel_series' THEN
     lunar_private.manifest((q.proposed_data->>'series')::uuid) ELSE '[]'::jsonb END,
   'conflicts',CASE WHEN q.proposed_data->>'operation' IN ('select','replace') THEN
     lunar_private.conflicts(q.proposed_data->'desired',q.event_id) ELSE '[]'::jsonb END)
 FROM public.schedule_change_requests q WHERE q.id=p_request
$$;

CREATE FUNCTION lunar_api.propose_series(p_action uuid,p_series uuid,p_purpose text,p_revision bigint,p_rule jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET TimeZone='UTC' SET DateStyle='ISO,YMD' AS $$
DECLARE subject bigint; s lunar_private.series%ROWTYPE; req bigint; command jsonb; old jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1); subject:=lunar_private.principal('owner');
 PERFORM lunar_private.validate_rule(p_rule);
 IF p_action IS NULL OR p_series IS NULL OR p_revision IS NULL OR p_purpose IS NULL OR
    p_purpose NOT IN ('birthday','wedding_anniversary','monthly') OR
    (p_purpose<>'monthly' AND p_rule->'month'='null'::jsonb) THEN
  RAISE EXCEPTION 'Invalid series' USING ERRCODE='22023'; END IF;
 command:=jsonb_build_object('action',p_action,'purpose',p_purpose,'series',p_series,'revision',p_revision,'rule',p_rule);
 SELECT q.id,q.proposed_data->'command' INTO req,old FROM public.schedule_change_requests q
 WHERE q.requested_by=subject AND q.proposed_data->>'api_version'='lunar-1'
 AND q.proposed_data->>'action'=p_action::text;
 IF FOUND THEN
  IF old IS DISTINCT FROM command THEN RAISE EXCEPTION 'Action mismatch' USING ERRCODE='22023'; END IF;
  RETURN req;
 END IF;
 INSERT INTO lunar_private.series(id,owner_subject,purpose) VALUES(p_series,subject,p_purpose) ON CONFLICT DO NOTHING;
 SELECT * INTO s FROM lunar_private.series WHERE id=p_series FOR UPDATE;
 IF s.owner_subject<>subject OR s.purpose<>p_purpose OR NOT s.enabled OR s.revision<>p_revision THEN
  RAISE EXCEPTION 'Series unavailable or stale' USING ERRCODE='22023'; END IF;
 INSERT INTO public.schedule_change_requests(action,requested_by,proposed_data)
 VALUES('add',subject,jsonb_build_object('api_version','lunar-1','operation','rule','action',p_action,
  'command',command,'series',p_series,'desired',p_rule,'original',lunar_private.snapshot(p_series,NULL))) RETURNING id INTO req;
 RETURN req;
END $$;

CREATE FUNCTION lunar_api.record_calculation(p_action uuid,p_series uuid,p_revision bigint,p_identity jsonb,
 p_profile text,p_evidence jsonb,p_date date) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET TimeZone='UTC' SET DateStyle='ISO,YMD' AS $$
DECLARE subject bigint; s lunar_private.series%ROWTYPE; o lunar_private.occurrences%ROWTYPE;
 c lunar_private.calculations%ROWTYPE; command jsonb; selection_ok boolean; producer oid;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1); subject:=lunar_private.principal('calculator');
 producer:=session_user::regrole::oid;
 IF p_action IS NULL OR p_identity IS NULL OR jsonb_typeof(p_identity)<>'object' OR
    NOT p_identity ?& ARRAY['version','convention','month','intercalation','lunation_cycle','paksha','tithi'] OR
    (SELECT count(*) FROM jsonb_object_keys(p_identity))<>7 OR p_identity->>'version'<>'2' OR jsonb_typeof(p_identity->'version')<>'number' OR
    EXISTS(SELECT FROM jsonb_each(p_identity) x WHERE x.value='null'::jsonb) OR
    jsonb_typeof(p_identity->'lunation_cycle')<>'number' OR
    (p_identity->>'lunation_cycle') !~ '^-?[0-9]+$' OR
    jsonb_typeof(p_identity->'tithi')<>'number' OR (p_identity->>'tithi') !~ '^(?:[1-9]|1[0-5])$' OR
    jsonb_typeof(p_evidence) IS DISTINCT FROM 'object' OR octet_length(p_evidence::text)>16000 OR
    NOT EXISTS(SELECT FROM lunar_private.profiles p WHERE p.digest=p_profile AND p.enabled) THEN
  RAISE EXCEPTION 'Unsupported calculation' USING ERRCODE='22023'; END IF;
 command:=jsonb_build_object('series',p_series,'revision',p_revision,'identity',p_identity,'profile',p_profile,
   'evidence',p_evidence,'date',p_date);
 -- Authorize the series before disclosing replay state.
 SELECT * INTO s FROM lunar_private.series WHERE id=p_series AND owner_subject=subject AND enabled FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Series unavailable' USING ERRCODE='22023'; END IF;
 SELECT * INTO c FROM lunar_private.calculations WHERE id=p_action;
 IF FOUND THEN
  IF c.producer<>producer OR c.producer_name<>session_user OR c.command IS DISTINCT FROM command THEN
   RAISE EXCEPTION 'Action mismatch' USING ERRCODE='22023'; END IF;
  RETURN c.occurrence_id;
 END IF;
 IF s.revision=0 OR s.revision IS DISTINCT FROM p_revision OR s.rule->>'profile' IS DISTINCT FROM p_profile OR
    s.rule->>'convention' IS DISTINCT FROM p_identity->>'convention' OR
    s.rule->>'paksha' IS DISTINCT FROM p_identity->>'paksha' OR
    s.rule->'tithi' IS DISTINCT FROM p_identity->'tithi' OR
    (s.rule->'month'<>'null'::jsonb AND s.rule->>'month' IS DISTINCT FROM p_identity->>'month') OR
    (s.rule->>'intercalation'<>'both' AND s.rule->>'intercalation' IS DISTINCT FROM p_identity->>'intercalation') THEN
  RAISE EXCEPTION 'Calculation rule unavailable or stale' USING ERRCODE='22023'; END IF;
 -- A producer assertion is NOT astronomical certification. Fail closed on any
 -- unresolved field; unsupported observations may be stored only without a date.
 selection_ok:=coalesce(p_evidence->>'status'='selected' AND p_evidence->>'month_status'='supported'
  AND p_evidence->>'date_gate'='pass' AND p_evidence->'kshaya'='false'::jsonb
  AND p_evidence->'ambiguous'='false'::jsonb AND p_evidence->'skipped'='false'::jsonb
  AND (p_evidence->'repeated'='false'::jsonb OR
       (p_evidence->'repeated'='true'::jsonb AND s.rule->>'repeated' IN ('first','last'))),false);
 IF p_date IS NOT NULL AND (NOT selection_ok OR NOT isfinite(p_date) OR
    p_date NOT BETWEEN date '1900-01-01' AND date '2100-12-31' OR
    p_evidence->>'selection' IS DISTINCT FROM to_char(p_date,'YYYY-MM-DD') OR
    p_evidence->>'birth_basis' IS DISTINCT FROM s.rule->>'birth_basis' OR
    p_evidence->>'repetition_policy' IS DISTINCT FROM s.rule->>'repeated' OR
    p_evidence->>'interval_start' IS NULL OR p_evidence->>'interval_end' IS NULL OR
    p_evidence->>'interval_start' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})$' OR
    p_evidence->>'interval_end' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})$' OR
    NOT isfinite((p_evidence->>'interval_start')::timestamptz) OR
    NOT isfinite((p_evidence->>'interval_end')::timestamptz) OR
    (p_evidence->>'interval_end')::timestamptz<=(p_evidence->>'interval_start')::timestamptz OR
    (p_evidence->>'interval_end')::timestamptz-(p_evidence->>'interval_start')::timestamptz>interval '3 days' OR
    ((p_evidence->>'interval_start')::timestamptz AT TIME ZONE 'Asia/Kolkata')::date>p_date OR
    (((p_evidence->>'interval_end')::timestamptz-interval '1 microsecond') AT TIME ZONE 'Asia/Kolkata')::date<p_date) THEN
  RAISE EXCEPTION 'Unselected lunar date' USING ERRCODE='22023'; END IF;
 INSERT INTO lunar_private.occurrences(series_id,convention,month,intercalation,lunation_cycle,paksha,tithi)
 VALUES(s.id,p_identity->>'convention',p_identity->>'month',p_identity->>'intercalation',
   (p_identity->>'lunation_cycle')::int,p_identity->>'paksha',(p_identity->>'tithi')::smallint)
 ON CONFLICT(series_id,convention,month,intercalation,lunation_cycle,paksha,tithi) DO NOTHING;
 SELECT * INTO o FROM lunar_private.occurrences WHERE series_id=s.id AND convention=p_identity->>'convention'
 AND month=p_identity->>'month' AND intercalation=p_identity->>'intercalation'
 AND lunation_cycle=(p_identity->>'lunation_cycle')::int AND paksha=p_identity->>'paksha'
 AND tithi=(p_identity->>'tithi')::smallint FOR UPDATE;
 INSERT INTO lunar_private.calculations(id,producer,command,occurrence_id,series_revision,profile,evidence,selection)
 VALUES(p_action,producer,command,o.id,s.revision,p_profile,p_evidence,p_date);
 -- Identical semantic evidence does not stale an overlapping-window proposal.
 IF o.calculation_id IS NULL OR EXISTS(SELECT FROM lunar_private.calculations old
    WHERE old.id=o.calculation_id AND old.command IS DISTINCT FROM command) THEN
  UPDATE lunar_private.occurrences SET calculation_id=p_action,observation=observation+1 WHERE id=o.id;
 END IF;
 RETURN o.id;
END $$;

CREATE FUNCTION lunar_api.propose_occurrence(p_action uuid,p_occurrence uuid,p_operation text,
 p_series_revision bigint,p_occurrence_revision bigint,p_observation bigint,p_desired jsonb) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET TimeZone='UTC' SET DateStyle='ISO,YMD' AS $$
DECLARE subject bigint; s lunar_private.series%ROWTYPE; o lunar_private.occurrences%ROWTYPE;
 c lunar_private.calculations%ROWTYPE; command jsonb; old jsonb; req bigint; data jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1); subject:=lunar_private.principal('owner');
 IF p_action IS NULL OR p_operation IS NULL OR p_operation NOT IN ('select','replace','cancel') THEN
  RAISE EXCEPTION 'Invalid operation' USING ERRCODE='22023'; END IF;
 SELECT s0.* INTO s FROM lunar_private.series s0 JOIN lunar_private.occurrences x ON x.series_id=s0.id
 WHERE x.id=p_occurrence AND s0.owner_subject=subject AND s0.enabled FOR UPDATE OF s0;
 IF NOT FOUND THEN RAISE EXCEPTION 'Occurrence unavailable' USING ERRCODE='22023'; END IF;
 SELECT * INTO o FROM lunar_private.occurrences WHERE id=p_occurrence FOR UPDATE;
 command:=jsonb_build_object('action',p_action,'occurrence',p_occurrence,'operation',p_operation,
   'series_revision',p_series_revision,'occurrence_revision',p_occurrence_revision,'observation',p_observation,'desired',p_desired);
 SELECT q.id,q.proposed_data->'command' INTO req,old FROM public.schedule_change_requests q
 WHERE q.requested_by=subject AND q.proposed_data->>'api_version'='lunar-1' AND q.proposed_data->>'action'=p_action::text;
 IF FOUND THEN
  IF old IS DISTINCT FROM command THEN RAISE EXCEPTION 'Action mismatch' USING ERRCODE='22023'; END IF;
  RETURN req;
 END IF;
 IF s.revision IS DISTINCT FROM p_series_revision OR o.revision IS DISTINCT FROM p_occurrence_revision OR
    o.observation IS DISTINCT FROM p_observation OR o.cancelled OR
    (p_operation='select' AND o.event_id IS NOT NULL) OR (p_operation IN ('replace','cancel') AND o.event_id IS NULL) THEN
  RAISE EXCEPTION 'Occurrence unavailable or stale' USING ERRCODE='22023'; END IF;
 SELECT * INTO c FROM lunar_private.calculations WHERE id=o.calculation_id;
 IF p_operation<>'cancel' THEN
  IF c.selection IS NULL OR c.series_revision<>s.revision OR jsonb_typeof(p_desired) IS DISTINCT FROM 'object' OR
     NOT p_desired ?& ARRAY['date','title','start_time'] OR EXISTS(SELECT FROM jsonb_object_keys(p_desired) k
      WHERE k NOT IN ('date','title','start_time','end_time')) OR
     p_desired->>'date' IS DISTINCT FROM to_char(c.selection,'YYYY-MM-DD') OR
     p_desired->>'start_time' !~ '^([01][0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9]([.][0-9]{1,6})?)?$' OR
     (p_desired ? 'end_time' AND p_desired->'end_time'<>'null'::jsonb AND
      p_desired->>'end_time' !~ '^([01][0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9]([.][0-9]{1,6})?)?$') OR
     jsonb_typeof(p_desired->'title') IS DISTINCT FROM 'string' OR
     jsonb_typeof(p_desired->'start_time') IS DISTINCT FROM 'string' OR
     length(p_desired->>'title') NOT BETWEEN 1 AND 200 OR
     (p_operation='select' AND (c.selection+(p_desired->>'start_time')::time) AT TIME ZONE 'Asia/Kolkata'<=clock_timestamp()) THEN
   RAISE EXCEPTION 'Invalid selected occurrence' USING ERRCODE='22023'; END IF;
  data:=(p_desired-'date')||jsonb_build_object('timezone','Asia/Kolkata','recurrence_rule',
    jsonb_build_object('calendar_system','gregorian','frequency','once','interval_count',1,'start_date',c.selection));
  PERFORM public.gregorian_validate(data);
 ELSIF p_desired IS DISTINCT FROM '{}'::jsonb THEN
  RAISE EXCEPTION 'Cancellation has no replacement payload' USING ERRCODE='22023';
 END IF;
 INSERT INTO public.schedule_change_requests(action,event_id,requested_by,proposed_data)
 VALUES(CASE WHEN p_operation='select' THEN 'add' WHEN p_operation='replace' THEN 'update' ELSE 'remove' END,
 o.event_id,subject,jsonb_build_object('api_version','lunar-1','action',p_action,'command',command,
 'operation',p_operation,'series',s.id,'occurrence',o.id,'calculation',o.calculation_id,'desired',p_desired,
 'original',lunar_private.snapshot(s.id,o.id))) RETURNING id INTO req;
 RETURN req;
END $$;

CREATE FUNCTION lunar_api.inspect_occurrence(p_occurrence uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET TimeZone='UTC' SET DateStyle='ISO,YMD' AS $$
DECLARE subject bigint; result jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1); subject:=lunar_private.principal('owner');
 SELECT lunar_private.snapshot(s.id,o.id) INTO result FROM lunar_private.series s
 JOIN lunar_private.occurrences o ON o.series_id=s.id WHERE o.id=p_occurrence AND s.owner_subject=subject;
 IF NOT FOUND THEN RAISE EXCEPTION 'Occurrence unavailable' USING ERRCODE='22023'; END IF;
 RETURN result;
END $$;

CREATE FUNCTION lunar_api.inspect_series(p_series uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET TimeZone='UTC' SET DateStyle='ISO,YMD' AS $$
DECLARE subject bigint; result jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1); subject:=lunar_private.principal('owner');
 SELECT jsonb_build_object('series',to_jsonb(s),'manifest',lunar_private.manifest(s.id)) INTO result
 FROM lunar_private.series s WHERE s.id=p_series AND s.owner_subject=subject;
 IF NOT FOUND THEN RAISE EXCEPTION 'Series unavailable' USING ERRCODE='22023'; END IF;
 RETURN result;
END $$;

CREATE FUNCTION lunar_api.propose_series_cancel(p_action uuid,p_series uuid,p_revision bigint,p_manifest jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET TimeZone='UTC' SET DateStyle='ISO,YMD' AS $$
DECLARE subject bigint; s lunar_private.series%ROWTYPE; command jsonb; old jsonb; req bigint; manifest jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1); subject:=lunar_private.principal('owner');
 IF p_action IS NULL THEN RAISE EXCEPTION 'Action required' USING ERRCODE='22023'; END IF;
 SELECT * INTO s FROM lunar_private.series WHERE id=p_series AND owner_subject=subject FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Series unavailable' USING ERRCODE='22023'; END IF;
 command:=jsonb_build_object('series',p_series,'revision',p_revision,'manifest',p_manifest);
 SELECT q.id,q.proposed_data->'command' INTO req,old FROM public.schedule_change_requests q
 WHERE q.requested_by=subject AND q.proposed_data->>'api_version'='lunar-1' AND q.proposed_data->>'action'=p_action::text;
 IF FOUND THEN
  IF old IS DISTINCT FROM command THEN RAISE EXCEPTION 'Action mismatch' USING ERRCODE='22023'; END IF;
  RETURN req;
 END IF;
 manifest:=lunar_private.manifest(s.id);
 IF NOT s.enabled OR s.revision IS DISTINCT FROM p_revision OR manifest IS DISTINCT FROM p_manifest OR
  jsonb_array_length(manifest)>64 THEN RAISE EXCEPTION 'Series manifest unavailable or stale' USING ERRCODE='22023'; END IF;
 INSERT INTO public.schedule_change_requests(action,requested_by,proposed_data) VALUES('remove',subject,
  jsonb_build_object('api_version','lunar-1','operation','cancel_series','action',p_action,'command',command,
   'series',s.id,'original',lunar_private.snapshot(s.id,NULL),'manifest',manifest)) RETURNING id INTO req;
 RETURN req;
END $$;

CREATE FUNCTION lunar_api.inspect_request(p_request bigint) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET TimeZone='UTC' SET DateStyle='ISO,YMD' AS $$
DECLARE subject bigint; reviewed jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1); subject:=lunar_private.principal('owner');
 IF NOT EXISTS(SELECT FROM public.schedule_change_requests q WHERE q.id=p_request AND q.requested_by=subject
  AND q.proposed_data->>'api_version'='lunar-1') THEN
  RAISE EXCEPTION 'Request unavailable' USING ERRCODE='22023'; END IF;
 reviewed:=lunar_private.review(p_request);
 RETURN reviewed||jsonb_build_object('fingerprint',lunar_private.hash(reviewed));
END $$;

CREATE FUNCTION lunar_api.decide(p_action uuid,p_request bigint,p_decision text,p_fingerprint text,
 p_reviewed boolean DEFAULT false,p_force boolean DEFAULT false) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET TimeZone='UTC' SET DateStyle='ISO,YMD' AS $$
DECLARE subject bigint; q public.schedule_change_requests%ROWTYPE; s lunar_private.series%ROWTYPE;
 o lunar_private.occurrences%ROWTYPE; a lunar_private.actions%ROWTYPE; command jsonb; reviewed jsonb;
 result jsonb; data jsonb; original jsonb; child bigint; ev bigint; good boolean; note text;
 operation text; desired jsonb; before_state jsonb; current_state jsonb; projection jsonb; same_projection boolean; member record;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1); subject:=lunar_private.principal('owner');
 IF p_action IS NULL OR p_decision IS NULL OR p_decision NOT IN ('approve','reject') OR
    p_reviewed IS NULL OR p_force IS NULL OR p_fingerprint IS NULL THEN
  RAISE EXCEPTION 'Invalid decision' USING ERRCODE='22023'; END IF;
 command:=jsonb_build_object('request',p_request,'decision',p_decision,'fingerprint',p_fingerprint,
   'reviewed',p_reviewed,'force',p_force);
 SELECT * INTO a FROM lunar_private.actions WHERE id=p_action;
 IF FOUND THEN
  IF a.principal<>session_user::regrole::oid OR a.principal_name<>session_user OR a.owner_subject<>subject
   OR a.command IS DISTINCT FROM command THEN
   RAISE EXCEPTION 'Action mismatch' USING ERRCODE='22023'; END IF;
  RETURN a.result;
 END IF;
 SELECT s0.* INTO s FROM lunar_private.series s0 JOIN public.schedule_change_requests q0
  ON s0.id=(q0.proposed_data->>'series')::uuid WHERE q0.id=p_request AND q0.requested_by=subject
  AND q0.proposed_data->>'api_version'='lunar-1' AND s0.owner_subject=subject FOR UPDATE OF s0;
 IF NOT FOUND THEN RAISE EXCEPTION 'Request unavailable' USING ERRCODE='22023'; END IF;
 SELECT * INTO q FROM public.schedule_change_requests WHERE id=p_request FOR UPDATE;
 SELECT * INTO o FROM lunar_private.occurrences WHERE id=(q.proposed_data->>'occurrence')::uuid FOR UPDATE;
 IF o.event_id IS NOT NULL THEN
  PERFORM FROM public.schedule_events WHERE id=o.event_id FOR UPDATE;
  PERFORM FROM public.reminder_deliveries WHERE event_id=o.event_id ORDER BY id FOR UPDATE;
 END IF;
 reviewed:=lunar_private.review(p_request); operation:=q.proposed_data->>'operation'; desired:=q.proposed_data->'desired';
 current_state:=lunar_private.snapshot(s.id,o.id); before_state:=current_state;
 IF q.status<>'pending' OR NOT s.enabled OR
    q.proposed_data->'original' IS DISTINCT FROM current_state OR
    p_fingerprint IS DISTINCT FROM lunar_private.hash(reviewed) THEN
  RAISE EXCEPTION 'Request unavailable or stale' USING ERRCODE='22023'; END IF;
 IF p_decision='reject' THEN
  UPDATE public.schedule_change_requests SET status='rejected',decided_at=now() WHERE id=q.id;
  result:=jsonb_build_object('status','rejected','request',q.id);
 ELSE
  IF NOT p_reviewed THEN RAISE EXCEPTION 'Explicit review required' USING ERRCODE='22023'; END IF;
  IF operation='rule' THEN
   PERFORM lunar_private.validate_rule(desired);
   IF EXISTS(SELECT FROM lunar_private.occurrences x WHERE x.series_id=s.id AND x.event_id IS NOT NULL)
     AND (s.rule-ARRAY['birth_basis','repeated','profile']) IS DISTINCT FROM
         (desired-ARRAY['birth_basis','repeated','profile']) THEN
    RAISE EXCEPTION 'Identity change requires reviewed mapping; unsupported here' USING ERRCODE='55000'; END IF;
   UPDATE lunar_private.series SET rule=desired,revision=revision+1 WHERE id=s.id;
  ELSIF operation='cancel_series' THEN
   IF q.proposed_data->'manifest' IS DISTINCT FROM lunar_private.manifest(s.id) THEN
    RAISE EXCEPTION 'Series manifest changed' USING ERRCODE='22023'; END IF;
   PERFORM FROM lunar_private.occurrences x WHERE x.series_id=s.id ORDER BY x.id FOR UPDATE;
   IF EXISTS(SELECT FROM public.reminder_deliveries d JOIN lunar_private.occurrences x ON x.event_id=d.event_id
      WHERE x.series_id=s.id AND d.status='sending') THEN
    RAISE EXCEPTION 'Delivery outcome unresolved' USING ERRCODE='55000'; END IF;
   FOR member IN SELECT x.* FROM lunar_private.occurrences x WHERE x.series_id=s.id
     AND x.event_id IS NOT NULL AND NOT x.cancelled ORDER BY x.id LOOP
    child:=public.propose_gregorian_change('remove','series',member.event_id,NULL,'{}'::jsonb,subject);
    SELECT x.success,x.message INTO good,note FROM public.decide_gregorian_change(child,subject,'approve',false,1) x;
    IF NOT good THEN RAISE EXCEPTION 'Native cancellation failed' USING ERRCODE='55000'; END IF;
    UPDATE public.reminder_deliveries SET status='cancelled' WHERE event_id=member.event_id
     AND managed_by='m2e' AND status IN ('pending','failed');
    UPDATE lunar_private.occurrences SET cancelled=true,revision=revision+1 WHERE id=member.id;
   END LOOP;
   UPDATE lunar_private.series SET enabled=false,revision=revision+1 WHERE id=s.id;
  ELSE
   IF o.cancelled OR o.id IS NULL THEN RAISE EXCEPTION 'Occurrence unavailable' USING ERRCODE='22023'; END IF;
   IF EXISTS(SELECT FROM public.reminder_deliveries d WHERE d.event_id=o.event_id AND d.status='sending') THEN
    RAISE EXCEPTION 'Delivery outcome unresolved' USING ERRCODE='55000'; END IF;
   IF operation<>'cancel' THEN
    projection:=public.gregorian_snapshot(o.event_id);
    same_projection:=o.event_id IS NOT NULL AND
     projection->'rule'->>'start_date'=desired->>'date' AND
     projection->'event'->>'title'=desired->>'title' AND
     (projection->'event'->>'start_time')::time=(desired->>'start_time')::time AND
     (projection->'event'->>'end_time')::time IS NOT DISTINCT FROM (desired->>'end_time')::time;
    IF NOT coalesce(same_projection,false) AND ((desired->>'date')::date IS NULL OR
       ((desired->>'date')::date+(desired->>'start_time')::time) AT TIME ZONE 'Asia/Kolkata'<=clock_timestamp()) THEN
     RAISE EXCEPTION 'Selected time is not future work' USING ERRCODE='22023'; END IF;
    IF NOT coalesce(same_projection,false) AND EXISTS(SELECT FROM public.reminder_deliveries d WHERE d.event_id=o.event_id
     AND (d.attempts<>0 OR d.status NOT IN ('pending','cancelled'))) THEN
     RAISE EXCEPTION 'Attempted delivery history prevents replacement' USING ERRCODE='55000'; END IF;
   END IF;
   -- Native conflict failure is handled in a subtransaction. It cannot leave a
   -- child request/event or an approved lunar request behind.
   BEGIN
    IF NOT coalesce(same_projection,false) OR operation='cancel' THEN
     data:=(desired-'date')||jsonb_build_object('timezone','Asia/Kolkata','recurrence_rule',
      jsonb_build_object('calendar_system','gregorian','frequency','once','interval_count',1,'start_date',desired->>'date'));
     child:=public.propose_gregorian_change(CASE WHEN operation='select' THEN 'add'
       WHEN operation='cancel' THEN 'remove' ELSE 'update' END,'series',o.event_id,NULL,
       CASE WHEN operation='cancel' THEN '{}'::jsonb ELSE data END,subject);
     SELECT x.success,x.message INTO good,note FROM public.decide_gregorian_change(child,subject,'approve',p_force,1) x;
     IF NOT good THEN RAISE EXCEPTION 'Conflict requires explicit reviewed approval' USING ERRCODE='P2001'; END IF;
     SELECT event_id INTO ev FROM public.schedule_change_requests WHERE id=child;
     IF operation<>'cancel' THEN
      UPDATE public.schedule_events SET event_date=(desired->>'date')::date WHERE id=ev;
     END IF;
     UPDATE public.reminder_deliveries SET status='cancelled' WHERE event_id=ev AND managed_by='m2e'
      AND status IN ('pending','failed') AND (operation='cancel' OR occurrence_date<>(desired->>'date')::date);
    ELSE ev:=o.event_id;
    END IF;
    UPDATE lunar_private.occurrences SET event_id=ev,revision=revision+1,cancelled=(operation='cancel') WHERE id=o.id;
   EXCEPTION WHEN SQLSTATE 'P2001' THEN
    result:=jsonb_build_object('status','conflict','request',q.id);
   END;
  END IF;
  IF result IS NULL THEN
   UPDATE public.schedule_change_requests SET status='approved',event_id=coalesce(ev,event_id),decided_at=now() WHERE id=q.id;
   result:=jsonb_build_object('status','approved','request',q.id,'event_id',ev);
  END IF;
 END IF;
 INSERT INTO lunar_private.actions(id,principal,owner_subject,request_id,command,result,snapshot)
 VALUES(p_action,session_user::regrole::oid,subject,q.id,command,result,jsonb_build_object('request',to_jsonb(q),
   'before',before_state,'after',lunar_private.snapshot(s.id,o.id),'review',reviewed,'child_request',child,
   'after_targets',CASE WHEN operation='cancel_series' THEN (SELECT jsonb_agg(
     lunar_private.snapshot(s.id,(v->'occurrence'->>'id')::uuid) ORDER BY v->'occurrence'->>'id')
     FROM jsonb_array_elements(q.proposed_data->'manifest') v) ELSE NULL END));
 RETURN result;
END $$;

-- Permit ONLY the trusted executor's lunar envelope through the earlier legacy
-- boundary; retain the original trigger body and every ordinary legacy check.
DO $migration$
DECLARE definition text; original text; wrapped text;
BEGIN
 SELECT pg_get_functiondef(p.oid),p.prosrc INTO definition,original FROM pg_proc p
 WHERE p.oid='public.guard_legacy_managed_request()'::regprocedure AND NOT p.prosecdef;
 IF NOT FOUND OR position('AS $function$'||original||'$function$' IN definition)=0 THEN
  RAISE EXCEPTION 'Legacy request guard requires explicit review'; END IF;
 wrapped:=E'BEGIN\nIF current_user=''dincharya_lunar_executor'' AND NEW.proposed_data->>''api_version''=''lunar-1'' THEN RETURN NEW; END IF;\n'
  ||E'<<preserved_legacy_guard>>\n'||original||E';\nEND;';
 EXECUTE replace(definition,'AS $function$'||original||'$function$','AS '||quote_literal(wrapped));
END $migration$;

-- Preserve the existing dispatcher body/properties; add explicit fail-closed
-- routing for lunar requests rather than passing them to legacy actor-ID APIs.
DO $migration$
DECLARE definition text; original text; wrapped text;
BEGIN
 SELECT pg_get_functiondef(p.oid),p.prosrc INTO definition,original FROM pg_proc p
 WHERE p.oid='public.dispatch_schedule_decision(bigint,bigint,text,boolean)'::regprocedure
 AND NOT p.prosecdef;
 IF NOT FOUND OR position('AS $function$'||original||'$function$' IN definition)=0 THEN
  RAISE EXCEPTION 'Dispatcher requires explicit review'; END IF;
 wrapped:=E'BEGIN\nIF EXISTS(SELECT FROM public.schedule_change_requests q WHERE q.id=p_request_id AND '
  ||E'q.requested_by=p_user_id AND q.proposed_data ? ''api_version'' AND '
  ||E'q.proposed_data->>''api_version'' IS DISTINCT FROM ''2'') THEN\n'
  ||E'RETURN QUERY SELECT false,''Use the authenticated calendar decision API''::text; RETURN; END IF;\n'
  ||E'<<preserved_dispatcher>>\n'||original||E';\nEND;';
 EXECUTE replace(definition,'AS $function$'||original||'$function$','AS '||quote_literal(wrapped));
END $migration$;

GRANT USAGE ON SCHEMA public,lunar_private TO dincharya_lunar_executor;
GRANT SELECT ON lunar_private.principals,lunar_private.profiles TO dincharya_lunar_executor;
GRANT SELECT,INSERT,UPDATE ON lunar_private.series,lunar_private.occurrences TO dincharya_lunar_executor;
GRANT SELECT,INSERT ON lunar_private.calculations,lunar_private.actions TO dincharya_lunar_executor;
GRANT SELECT,INSERT,UPDATE ON public.schedule_events,public.recurrence_rules,public.schedule_change_requests TO dincharya_lunar_executor;
GRANT SELECT,UPDATE(status) ON public.reminder_deliveries TO dincharya_lunar_executor;
GRANT SELECT ON public.schedule_occurrence_overrides TO dincharya_lunar_executor;
DO $$ DECLARE target regclass; tbl text; BEGIN
 FOREACH tbl IN ARRAY ARRAY['schedule_events','recurrence_rules','schedule_change_requests'] LOOP
  target:=pg_get_serial_sequence('public.'||tbl,'id')::regclass;
  IF target IS NOT NULL THEN EXECUTE format('GRANT USAGE ON SEQUENCE %s TO dincharya_lunar_executor',target); END IF;
 END LOOP;
END $$;
-- Each SECURITY DEFINER entry point has a non-login, non-superuser owner. No
-- owner/calculator caller can SET ROLE into it. Public native APIs remain
-- invoker functions, so revoked raw DML cannot be bypassed through them.
DO $$ DECLARE f record; BEGIN
 FOR f IN SELECT p.oid::regprocedure signature FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
  WHERE n.nspname IN ('lunar_api','lunar_private') LOOP
  EXECUTE format('ALTER FUNCTION %s OWNER TO dincharya_lunar_executor',f.signature);
 END LOOP;
END $$;
ALTER FUNCTION public.lunar_projection_is_mapped(bigint) OWNER TO dincharya_lunar_executor;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA lunar_api,lunar_private FROM PUBLIC;
GRANT USAGE ON SCHEMA lunar_api TO dincharya_lunar_owner,dincharya_lunar_calculator;
GRANT EXECUTE ON FUNCTION lunar_api.propose_series(uuid,uuid,text,bigint,jsonb),
 lunar_api.propose_occurrence(uuid,uuid,text,bigint,bigint,bigint,jsonb),
 lunar_api.inspect_occurrence(uuid),lunar_api.inspect_series(uuid),lunar_api.propose_series_cancel(uuid,uuid,bigint,jsonb),
 lunar_api.inspect_request(bigint),lunar_api.decide(uuid,bigint,text,text,boolean,boolean) TO dincharya_lunar_owner;
GRANT EXECUTE ON FUNCTION lunar_api.record_calculation(uuid,uuid,bigint,jsonb,text,jsonb,date) TO dincharya_lunar_calculator;
REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON public.schedule_events,public.recurrence_rules,
 public.schedule_occurrence_overrides,public.schedule_change_requests FROM PUBLIC;

-- Remove pre-existing direct grants too; PUBLIC revocation alone is insufficient.
-- This setup is guarded to fresh synthetic databases, never a production ACL rollout.
DO $$ DECLARE r record; BEGIN
 FOR r IN SELECT rolname FROM pg_roles WHERE NOT rolsuper AND rolname<>'dincharya_lunar_executor' LOOP
  EXECUTE format('REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON public.schedule_events,public.recurrence_rules,public.schedule_occurrence_overrides,public.schedule_change_requests FROM %I',r.rolname);
 END LOOP;
END $$;
