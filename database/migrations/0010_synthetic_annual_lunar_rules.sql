-- Durable annual rule metadata over the already reviewed lunar approval API.
-- This migration is restricted to the existing disposable environment.
DO $$ BEGIN
 IF current_database()<>'dincharya_app_test' OR session_user<>'synthetic_test' THEN
  RAISE EXCEPTION 'Isolated synthetic lunar setup required';
 END IF;
END $$;

CREATE TABLE lunar_private.annual_rules (
 series_id uuid PRIMARY KEY REFERENCES lunar_private.series,
 start_year integer NOT NULL CHECK(start_year BETWEEN 2000 AND 2099),
 title text NOT NULL CHECK(length(title) BETWEEN 1 AND 80 AND title !~ '[[:cntrl:]]'),
 appointment_time time NOT NULL CHECK(appointment_time<time '24:00'),
 approved_request bigint NOT NULL UNIQUE REFERENCES public.schedule_change_requests,
 approved_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TRIGGER annual_rule_immutable BEFORE UPDATE OR DELETE ON lunar_private.annual_rules
 FOR EACH ROW EXECUTE FUNCTION lunar_private.immutable();
CREATE TRIGGER annual_rule_no_truncate BEFORE TRUNCATE ON lunar_private.annual_rules
 FOR EACH STATEMENT EXECUTE FUNCTION lunar_private.immutable();
GRANT SELECT,INSERT ON lunar_private.annual_rules TO dincharya_lunar_executor;
-- The non-login executor invokes the existing scoped wrappers; their
-- principal checks still resolve the original authenticated session_user.
GRANT USAGE ON SCHEMA lunar_api TO dincharya_lunar_executor;

CREATE FUNCTION lunar_api.approve_annual_rule(
 p_series uuid,p_proposal uuid,p_decision uuid,p_purpose text,p_rule jsonb,
 p_start_year integer,p_title text,p_time time,p_expires timestamptz
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET TimeZone='UTC' SET DateStyle='ISO,YMD' AS $$
DECLARE subject bigint; existing lunar_private.annual_rules%ROWTYPE; snapshot jsonb;
 req bigint; decision jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 subject:=lunar_private.principal('owner');
 IF p_expires IS NULL OR NOT isfinite(p_expires) OR p_expires<=clock_timestamp()
    OR p_expires>clock_timestamp()+interval '30 minutes' THEN
  RAISE EXCEPTION 'Annual rule review expired' USING ERRCODE='22023';
 END IF;
 IF p_series IS NULL OR p_proposal IS NULL OR p_decision IS NULL
    OR p_start_year IS NULL OR p_start_year NOT BETWEEN 2000 AND 2099
    OR p_title IS NULL OR length(p_title) NOT BETWEEN 1 AND 80 OR p_title ~ '[[:cntrl:]]'
    OR p_time IS NULL OR p_time>=time '24:00' OR extract(second FROM p_time)<>0
    OR p_purpose IS NULL OR p_rule->>'month' IS NULL
    OR coalesce(p_rule->>'intercalation','') NOT IN ('ordinary','adhika') THEN
  RAISE EXCEPTION 'Invalid annual lunar rule' USING ERRCODE='22023';
 END IF;
 PERFORM lunar_private.validate_rule(p_rule);
 SELECT a.* INTO existing FROM lunar_private.annual_rules a
  JOIN lunar_private.series s ON s.id=a.series_id
  WHERE a.series_id=p_series AND s.owner_subject=subject;
 IF FOUND THEN
  snapshot:=lunar_api.inspect_series(p_series)->'series';
  IF snapshot->'rule' IS DISTINCT FROM p_rule OR snapshot->>'purpose' IS DISTINCT FROM p_purpose
     OR (existing.title,existing.appointment_time,existing.start_year)
          IS DISTINCT FROM (p_title,p_time,p_start_year) THEN
   RAISE EXCEPTION 'Annual rule changed; inspect the existing series' USING ERRCODE='22023';
  END IF;
  IF NOT (snapshot->>'enabled')::boolean THEN
   RETURN jsonb_build_object('status','series_cancelled','series',p_series);
  END IF;
  RETURN jsonb_build_object('status','approved','series',p_series);
 END IF;

 -- A pre-existing non-annual series must never be silently converted.
 IF EXISTS(SELECT FROM lunar_private.series s WHERE s.id=p_series) THEN
  RAISE EXCEPTION 'Annual series unavailable' USING ERRCODE='22023';
 END IF;
 req:=lunar_api.propose_series(p_proposal,p_series,p_purpose,0,p_rule);
 snapshot:=lunar_api.inspect_request(req);
 decision:=lunar_api.decide(p_decision,req,'approve',snapshot->>'fingerprint',true,false);
 IF decision->>'status' IS DISTINCT FROM 'approved' THEN
  RAISE EXCEPTION 'Annual rule approval failed' USING ERRCODE='22023';
 END IF;
 INSERT INTO lunar_private.annual_rules(series_id,start_year,title,appointment_time,approved_request)
 VALUES(p_series,p_start_year,p_title,p_time,req);
 RETURN jsonb_build_object('status','approved','series',p_series);
END $$;

CREATE FUNCTION lunar_api.inspect_annual_rule(p_series uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET TimeZone='UTC' SET DateStyle='ISO,YMD' AS $$
DECLARE subject bigint; details jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 subject:=lunar_private.principal('owner');
 SELECT jsonb_build_object('annual',to_jsonb(a),'series',to_jsonb(s)) INTO details
  FROM lunar_private.annual_rules a JOIN lunar_private.series s ON s.id=a.series_id
  WHERE s.id=p_series AND s.owner_subject=subject;
 IF NOT FOUND THEN RAISE EXCEPTION 'Annual series unavailable' USING ERRCODE='22023'; END IF;
 RETURN details;
END $$;

CREATE FUNCTION lunar_api.list_annual_rules(p_after uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET TimeZone='UTC' AS $$
DECLARE subject bigint;
BEGIN
 subject:=lunar_private.principal('owner');
 RETURN (SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY x.series_id),'[]'::jsonb)
  FROM (SELECT a.series_id,a.title,a.start_year,s.enabled FROM lunar_private.annual_rules a
   JOIN lunar_private.series s ON s.id=a.series_id WHERE s.owner_subject=subject
   AND (p_after IS NULL OR a.series_id>p_after) ORDER BY a.series_id LIMIT 10) x);
END $$;

ALTER FUNCTION lunar_api.approve_annual_rule(uuid,uuid,uuid,text,jsonb,integer,text,time,timestamptz)
 OWNER TO dincharya_lunar_executor;
ALTER FUNCTION lunar_api.inspect_annual_rule(uuid) OWNER TO dincharya_lunar_executor;
ALTER FUNCTION lunar_api.list_annual_rules(uuid) OWNER TO dincharya_lunar_executor;
REVOKE ALL ON FUNCTION lunar_api.approve_annual_rule(uuid,uuid,uuid,text,jsonb,integer,text,time,timestamptz),
 lunar_api.inspect_annual_rule(uuid),lunar_api.list_annual_rules(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION lunar_api.approve_annual_rule(uuid,uuid,uuid,text,jsonb,integer,text,time,timestamptz),
 lunar_api.inspect_annual_rule(uuid),lunar_api.list_annual_rules(uuid) TO dincharya_lunar_owner;

-- Apply the annual contract even when a trusted caller uses the existing
-- approval API directly. The common lock serializes this check with projection.
CREATE FUNCTION lunar_private.guard_annual_projection() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE metadata lunar_private.annual_rules%ROWTYPE; event public.schedule_events%ROWTYPE;
 target_year integer;
BEGIN
 IF NEW.event_id IS NULL THEN RETURN NEW; END IF;
 PERFORM pg_advisory_xact_lock(20261112,1);
 SELECT * INTO metadata FROM lunar_private.annual_rules WHERE series_id=NEW.series_id;
 IF NOT FOUND THEN RETURN NEW; END IF;
 SELECT * INTO event FROM public.schedule_events WHERE id=NEW.event_id;
 target_year:=extract(year FROM event.event_date);
 IF event.title IS DISTINCT FROM metadata.title OR event.start_time IS DISTINCT FROM metadata.appointment_time
    OR event.end_time IS NOT NULL OR target_year IS NULL OR target_year NOT BETWEEN metadata.start_year AND 2099 THEN
  RAISE EXCEPTION 'Annual appointment does not match its rule' USING ERRCODE='22023';
 END IF;
 IF EXISTS(SELECT FROM lunar_private.occurrences o JOIN public.schedule_events e ON e.id=o.event_id
    WHERE o.series_id=NEW.series_id AND o.id<>NEW.id AND extract(year FROM e.event_date)=target_year) THEN
  RAISE EXCEPTION 'Annual appointment year already used' USING ERRCODE='22023';
 END IF;
 IF OLD.event_id IS NULL AND (SELECT count(*) FROM lunar_private.occurrences o
    WHERE o.series_id=NEW.series_id AND o.event_id IS NOT NULL AND NOT o.cancelled)>=64 THEN
  RAISE EXCEPTION 'Annual series manifest limit reached' USING ERRCODE='22023';
 END IF;
 RETURN NEW;
END $$;
ALTER FUNCTION lunar_private.guard_annual_projection() OWNER TO dincharya_lunar_executor;
REVOKE ALL ON FUNCTION lunar_private.guard_annual_projection() FROM PUBLIC;
CREATE TRIGGER guard_annual_projection BEFORE UPDATE OF event_id ON lunar_private.occurrences
 FOR EACH ROW WHEN (NEW.event_id IS NOT NULL AND NOT NEW.cancelled)
 EXECUTE FUNCTION lunar_private.guard_annual_projection();

CREATE FUNCTION lunar_private.guard_annual_rule_update() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF EXISTS(SELECT FROM lunar_private.annual_rules WHERE series_id=OLD.id)
    AND (NEW.rule IS DISTINCT FROM OLD.rule OR (NOT OLD.enabled AND NEW.enabled)) THEN
  RAISE EXCEPTION 'Annual rule changes require separate review' USING ERRCODE='22023';
 END IF;
 RETURN NEW;
END $$;
ALTER FUNCTION lunar_private.guard_annual_rule_update() OWNER TO dincharya_lunar_executor;
REVOKE ALL ON FUNCTION lunar_private.guard_annual_rule_update() FROM PUBLIC;
CREATE TRIGGER guard_annual_rule_update BEFORE UPDATE ON lunar_private.series
 FOR EACH ROW EXECUTE FUNCTION lunar_private.guard_annual_rule_update();

-- A queued decision must still be fresh after acquiring the common write lock.
CREATE FUNCTION lunar_api.decide_annual_review(
 p_action uuid,p_request bigint,p_decision text,p_fingerprint text,p_expires timestamptz
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET TimeZone='UTC' SET DateStyle='ISO,YMD' AS $$
DECLARE reviewed jsonb; proposal jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 reviewed:=lunar_api.inspect_request(p_request);
 IF p_expires IS NULL OR NOT isfinite(p_expires) OR p_expires<=clock_timestamp()
    OR p_expires>clock_timestamp()+interval '30 minutes' THEN
  RAISE EXCEPTION 'Annual review expired' USING ERRCODE='22023';
 END IF;
 proposal:=reviewed->'proposal';
 IF proposal->>'operation' NOT IN ('select','cancel','cancel_series')
    OR NOT EXISTS(SELECT FROM lunar_private.annual_rules WHERE series_id=(proposal->>'series')::uuid) THEN
  RAISE EXCEPTION 'Annual request unavailable' USING ERRCODE='22023';
 END IF;
 RETURN lunar_api.decide(p_action,p_request,p_decision,p_fingerprint,true,false);
END $$;
ALTER FUNCTION lunar_api.decide_annual_review(uuid,bigint,text,text,timestamptz)
 OWNER TO dincharya_lunar_executor;
REVOKE ALL ON FUNCTION lunar_api.decide_annual_review(uuid,bigint,text,text,timestamptz) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION lunar_api.decide_annual_review(uuid,bigint,text,text,timestamptz) TO dincharya_lunar_owner;
