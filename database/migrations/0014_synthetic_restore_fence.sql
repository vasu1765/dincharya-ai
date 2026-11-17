-- Isolated synthetic cross-cluster recovery. Never rewrite original approval evidence.
DO $$ BEGIN
 IF current_database()<>'dincharya_app_test' OR session_user<>'synthetic_test' THEN
  RAISE EXCEPTION 'Isolated synthetic setup required';
 END IF;
END $$;

CREATE TABLE lunar_private.restore_epoch (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE lunar_private.restored_pending_request (
 request_id bigint PRIMARY KEY REFERENCES public.schedule_change_requests(id),
 epoch uuid NOT NULL REFERENCES lunar_private.restore_epoch(id)
);
CREATE TABLE lunar_private.restored_partial_occurrence (
 occurrence_id uuid PRIMARY KEY REFERENCES lunar_private.occurrences(id),
 epoch uuid NOT NULL REFERENCES lunar_private.restore_epoch(id)
);

CREATE TRIGGER immutable_restore_epoch BEFORE UPDATE OR DELETE ON lunar_private.restore_epoch
 FOR EACH ROW EXECUTE FUNCTION lunar_private.immutable();
CREATE TRIGGER immutable_restored_request BEFORE UPDATE OR DELETE ON lunar_private.restored_pending_request
 FOR EACH ROW EXECUTE FUNCTION lunar_private.immutable();
CREATE TRIGGER immutable_restored_occurrence BEFORE UPDATE OR DELETE ON lunar_private.restored_partial_occurrence
 FOR EACH ROW EXECUTE FUNCTION lunar_private.immutable();

GRANT SELECT ON lunar_private.restore_epoch,lunar_private.restored_partial_occurrence,
 lunar_private.restored_pending_request TO dincharya_lunar_executor;

-- Run offline in the restored database in the same transaction as the independently
-- verified role rebind. The application and worker have no EXECUTE privilege.
CREATE FUNCTION lunar_private.fence_restored_pending() RETURNS uuid
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE stamp uuid;
BEGIN
 IF current_database()<>'dincharya_app_test' OR session_user<>'synthetic_test' THEN
  RAISE EXCEPTION 'Isolated recovery administrator required' USING ERRCODE='42501';
 END IF;
 PERFORM pg_advisory_xact_lock(20261112,1);
 INSERT INTO lunar_private.restore_epoch DEFAULT VALUES RETURNING id INTO stamp;
 INSERT INTO lunar_private.restored_pending_request
 SELECT id,stamp FROM public.schedule_change_requests WHERE status='pending'
 ON CONFLICT DO NOTHING;
 INSERT INTO lunar_private.restored_partial_occurrence
 SELECT id,stamp FROM lunar_private.occurrences WHERE event_id IS NULL AND NOT cancelled
 ON CONFLICT DO NOTHING;
 RETURN stamp;
END $$;
REVOKE ALL ON FUNCTION lunar_private.fence_restored_pending() FROM PUBLIC;

CREATE FUNCTION lunar_private.guard_restored_request() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF EXISTS(SELECT FROM lunar_private.restored_pending_request WHERE request_id=OLD.id) THEN
  RAISE EXCEPTION 'Restored pending decision requires a new review' USING ERRCODE='42501';
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$;
REVOKE ALL ON FUNCTION lunar_private.guard_restored_request() FROM PUBLIC;
CREATE TRIGGER guard_restored_request BEFORE UPDATE OR DELETE ON public.schedule_change_requests
 FOR EACH ROW EXECUTE FUNCTION lunar_private.guard_restored_request();

CREATE FUNCTION lunar_api.restore_epoch() RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM lunar_private.principal('owner');
 RETURN (SELECT id FROM lunar_private.restore_epoch ORDER BY recorded_at DESC,id DESC LIMIT 1);
END $$;
ALTER FUNCTION lunar_api.restore_epoch() OWNER TO dincharya_lunar_executor;
REVOKE ALL ON FUNCTION lunar_api.restore_epoch() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION lunar_api.restore_epoch() TO dincharya_lunar_owner;

CREATE FUNCTION lunar_api.request_requires_new_review(p_request bigint) RETURNS boolean
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT EXISTS(SELECT FROM lunar_private.restored_pending_request h
  JOIN public.schedule_change_requests q ON q.id=h.request_id
  WHERE h.request_id=p_request AND q.requested_by=lunar_private.principal('owner'))
$$;
ALTER FUNCTION lunar_api.request_requires_new_review(bigint) OWNER TO dincharya_lunar_executor;
REVOKE ALL ON FUNCTION lunar_api.request_requires_new_review(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION lunar_api.request_requires_new_review(bigint) TO dincharya_lunar_owner;

ALTER FUNCTION lunar_api.project_recurring(uuid,integer,uuid,uuid,uuid,bigint)
 RENAME TO project_before_restore_fence;
REVOKE ALL ON FUNCTION lunar_api.project_before_restore_fence(uuid,integer,uuid,uuid,uuid,bigint)
 FROM dincharya_lunar_owner;

CREATE FUNCTION lunar_api.project_recurring(
 p_control uuid,p_revision integer,p_occurrence uuid,p_action uuid,p_decision uuid,p_observation bigint
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE subject bigint;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 subject:=lunar_private.principal('owner');
 IF EXISTS(SELECT FROM lunar_private.restored_partial_occurrence h
  JOIN lunar_private.occurrences o ON o.id=h.occurrence_id
  JOIN lunar_private.recurring_control c ON c.series_id=o.series_id
  WHERE o.id=p_occurrence AND o.event_id IS NULL AND c.id=p_control
   AND c.owner_subject=subject AND c.revision=p_revision AND c.state='active' AND c.mode='automatic') THEN
  RETURN jsonb_build_object('status','restore_review_required');
 END IF;
 RETURN lunar_api.project_before_restore_fence(p_control,p_revision,p_occurrence,p_action,p_decision,p_observation);
END $$;
ALTER FUNCTION lunar_api.project_recurring(uuid,integer,uuid,uuid,uuid,bigint) OWNER TO dincharya_lunar_executor;
REVOKE ALL ON FUNCTION lunar_api.project_recurring(uuid,integer,uuid,uuid,uuid,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION lunar_api.project_recurring(uuid,integer,uuid,uuid,uuid,bigint) TO dincharya_lunar_owner;
