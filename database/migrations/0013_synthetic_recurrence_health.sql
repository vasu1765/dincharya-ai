-- Health aggregation only. Historical provenance remains in the existing review ledger.
DO $$ BEGIN
 IF current_database()<>'dincharya_app_test' OR session_user<>'synthetic_test' THEN
  RAISE EXCEPTION 'Isolated synthetic setup required';
 END IF;
END $$;

CREATE TABLE lunar_private.recurring_health (
 owner_subject bigint PRIMARY KEY,
 projected_at timestamptz NOT NULL CHECK (isfinite(projected_at))
);
GRANT SELECT,INSERT,UPDATE ON lunar_private.recurring_health TO dincharya_lunar_executor;

CREATE FUNCTION lunar_api.mark_recurring_success() RETURNS void
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 INSERT INTO lunar_private.recurring_health AS h VALUES(lunar_private.principal('owner'),clock_timestamp())
 ON CONFLICT(owner_subject) DO UPDATE SET projected_at=greatest(h.projected_at,excluded.projected_at)
$$;

CREATE FUNCTION lunar_api.recurring_health() RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 WITH scoped_events AS (
  SELECT c.event_id FROM lunar_private.recurring_control c
   WHERE c.owner_subject=lunar_private.principal('owner') AND c.event_id IS NOT NULL
  UNION
  SELECT o.event_id FROM lunar_private.recurring_control c
   JOIN lunar_private.occurrences o ON c.series_id=o.series_id
   WHERE c.owner_subject=lunar_private.principal('owner') AND o.event_id IS NOT NULL
 )
 SELECT jsonb_build_object(
  'last_projection',(SELECT projected_at FROM lunar_private.recurring_health
                      WHERE owner_subject=lunar_private.principal('owner')),
  'due',count(*) FILTER (WHERE s.status IN ('pending','failed') AND s.due_at<=clock_timestamp()),
  'sending',count(*) FILTER (WHERE s.status='sending'),
  'uncertain',count(*) FILTER (WHERE s.status='uncertain'),
  'dead',count(*) FILTER (WHERE s.status='dead'),
  'last_confirmed_due',max(s.due_at) FILTER (WHERE s.status='sent'),
  'quarantine',(SELECT coalesce(jsonb_agg(to_jsonb(q)),'[]') FROM
    (SELECT x.id,x.event_id,x.occurrence_date,x.offset_minutes,x.due_at,x.attempts
     FROM lunar_private.notification_slot x JOIN scoped_events e USING(event_id)
     WHERE x.status='uncertain' ORDER BY x.id LIMIT 20) q))
 FROM lunar_private.notification_slot s JOIN scoped_events e USING(event_id)
$$;

ALTER FUNCTION lunar_api.mark_recurring_success() OWNER TO dincharya_lunar_executor;
ALTER FUNCTION lunar_api.recurring_health() OWNER TO dincharya_lunar_executor;
REVOKE ALL ON FUNCTION lunar_api.mark_recurring_success(),lunar_api.recurring_health() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION lunar_api.mark_recurring_success(),lunar_api.recurring_health() TO dincharya_lunar_owner;
