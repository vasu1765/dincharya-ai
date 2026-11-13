-- Owner-scoped read-only delivery metadata for authenticated gateway status.
DO $$ BEGIN
 IF current_database()<>'dincharya_app_test' OR session_user<>'synthetic_test' THEN
  RAISE EXCEPTION 'Isolated synthetic installation required'; END IF;
END $$;
CREATE FUNCTION lunar_api.delivery_status(p_occurrence uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET TimeZone='UTC' AS $$
DECLARE subject bigint; occurrence lunar_private.occurrences%ROWTYPE;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);subject:=lunar_private.principal('owner');
 SELECT o.* INTO occurrence FROM lunar_private.occurrences o JOIN lunar_private.series s ON s.id=o.series_id
 WHERE o.id=p_occurrence AND s.owner_subject=subject;
 IF NOT FOUND THEN RAISE EXCEPTION 'Occurrence unavailable' USING ERRCODE='22023'; END IF;
 RETURN jsonb_build_object('occurrence',occurrence.id,'event_id',occurrence.event_id,'cancelled',occurrence.cancelled,
  'revision',occurrence.revision,'deliveries',coalesce((SELECT jsonb_agg(jsonb_build_object(
    'state',d.status,'attempts',d.attempts,'due_at',d.due_at,'has_receipt',d.telegram_message_id IS NOT NULL) ORDER BY d.id)
    FROM (SELECT * FROM public.reminder_deliveries d0 WHERE d0.event_id=occurrence.event_id ORDER BY d0.id DESC LIMIT 20) d),'[]'::jsonb),
  'limited_to',20);
END $$;
ALTER FUNCTION lunar_api.delivery_status(uuid) OWNER TO dincharya_lunar_executor;
REVOKE ALL ON FUNCTION lunar_api.delivery_status(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION lunar_api.delivery_status(uuid) TO dincharya_lunar_owner;
CREATE FUNCTION lunar_api.owner_identity() RETURNS bigint
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT lunar_private.principal('owner')
$$;
ALTER FUNCTION lunar_api.owner_identity() OWNER TO dincharya_lunar_executor;
REVOKE ALL ON FUNCTION lunar_api.owner_identity() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION lunar_api.owner_identity() TO dincharya_lunar_owner;
