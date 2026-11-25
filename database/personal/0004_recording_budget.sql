-- Every recording epoch has six outbound operations shared by UI and reminder paths.
BEGIN;
DO $$ BEGIN
 IF current_database()<>'dincharya_personal_candidate' OR current_setting('server_version_num')::int/10000<>17
 THEN RAISE EXCEPTION 'fresh PG17 candidate required'; END IF;
END $$;
SET LOCAL ROLE personal_executor;
CREATE TABLE beta.recording_budget(epoch uuid PRIMARY KEY, used integer NOT NULL CHECK(used BETWEEN 1 AND 6));
CREATE FUNCTION beta.reserve_recording(actor bigint,bot_id bigint) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE ep uuid;
BEGIN
 ep:=beta.ui_owner(actor,bot_id);
 INSERT INTO beta.recording_budget AS b VALUES(ep,1)
 ON CONFLICT(epoch) DO UPDATE SET used=b.used+1 WHERE b.used<6;
 RETURN FOUND;
END $$;
REVOKE ALL ON FUNCTION beta.reserve_recording(bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION beta.reserve_recording(bigint,bigint) TO personal_gateway;
CREATE FUNCTION beta.recording_ready() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $
 SELECT beta.owned('personal_worker') AND h.enabled AND h.poller AND h.worker
 AND h.uncertain=0 AND h.ui_unsettled=0 FROM beta.health() h;
$;
CREATE FUNCTION beta.recording_claim() RETURNS TABLE(slot_id bigint,token uuid,recipient bigint,title text,starts timestamptz)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $
BEGIN
 IF NOT beta.recording_ready() THEN RAISE EXCEPTION 'recording requires inspection'; END IF;
 PERFORM pg_advisory_xact_lock(18890421);
 UPDATE beta.slot SET state='uncertain',lease=NULL,deadline=NULL WHERE state='sending' AND deadline<=clock_timestamp();
 IF FOUND THEN RETURN; END IF;
 RETURN QUERY SELECT * FROM beta.claim_notice();
END $;
REVOKE ALL ON FUNCTION beta.recording_ready(),beta.recording_claim() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION beta.recording_ready(),beta.recording_claim() TO personal_worker;
COMMIT;
