-- Invented transport evidence ONLY. Installed by test harness in disposable DB.
DO $$ BEGIN IF current_database()<>'dincharya_app_test' OR session_user<>'synthetic_test' THEN
 RAISE EXCEPTION 'Disposable fixture required'; END IF; END $$;
CREATE SCHEMA synthetic_e2e;
REVOKE ALL ON SCHEMA synthetic_e2e FROM PUBLIC;
CREATE ROLE synthetic_e2e_transport_executor NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE TABLE synthetic_e2e.attempts (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,event_id bigint NOT NULL REFERENCES public.schedule_events,
 mode text NOT NULL CHECK(mode IN ('success','failure','uncertain')),accepted boolean NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TRIGGER immutable_transport_attempts BEFORE UPDATE OR DELETE ON synthetic_e2e.attempts
 FOR EACH ROW EXECUTE FUNCTION lunar_private.immutable();
CREATE TRIGGER immutable_transport_attempts_truncate BEFORE TRUNCATE ON synthetic_e2e.attempts
 FOR EACH STATEMENT EXECUTE FUNCTION lunar_private.immutable();
GRANT USAGE ON SCHEMA public,synthetic_e2e TO synthetic_e2e_transport_executor;
GRANT SELECT ON public.reminder_deliveries TO synthetic_e2e_transport_executor;
GRANT INSERT,SELECT ON synthetic_e2e.attempts TO synthetic_e2e_transport_executor;
GRANT USAGE ON SEQUENCE synthetic_e2e.attempts_id_seq TO synthetic_e2e_transport_executor;
CREATE FUNCTION synthetic_e2e.record_attempt(p_event bigint,p_mode text) RETURNS TABLE(message_id bigint)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$ BEGIN
 IF current_database()<>'dincharya_app_test' OR session_user<>'synthetic_e2e_transport' OR
   NOT EXISTS(SELECT FROM public.reminder_deliveries d WHERE d.event_id=p_event AND d.managed_by='m2e'
    AND d.status='sending' AND d.lease_until>clock_timestamp()) THEN
  RAISE EXCEPTION 'Synthetic transport unavailable' USING ERRCODE='42501'; END IF;
 RETURN QUERY INSERT INTO synthetic_e2e.attempts(event_id,mode,accepted) VALUES(p_event,p_mode,p_mode<>'failure') RETURNING id;
END $$;
ALTER FUNCTION synthetic_e2e.record_attempt(bigint,text) OWNER TO synthetic_e2e_transport_executor;
REVOKE ALL ON FUNCTION synthetic_e2e.record_attempt(bigint,text) FROM PUBLIC;
