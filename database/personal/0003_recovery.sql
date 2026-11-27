BEGIN;
DO $$ BEGIN
 IF current_database()<>'dincharya_personal_candidate' OR current_setting('server_version_num')::int/10000<>17
 THEN RAISE EXCEPTION 'Fresh PG17 candidate required'; END IF;
END $$;
SET LOCAL ROLE personal_executor;
CREATE SEQUENCE beta.recorded_message;
CREATE FUNCTION beta.recorded_id() RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF NOT (beta.owned('personal_gateway') OR beta.owned('personal_worker')) OR NOT EXISTS(SELECT FROM beta.authority WHERE enabled)
 THEN RAISE EXCEPTION 'recording fenced'; END IF;
 RETURN nextval('beta.recorded_message');
END $$;
GRANT EXECUTE ON FUNCTION beta.recorded_id() TO personal_gateway,personal_worker;
CREATE FUNCTION beta.health() RETURNS TABLE(enabled boolean,poller boolean,worker boolean,
 pending bigint,uncertain bigint,ui_unsettled bigint,oldest_due_seconds bigint)
 LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT coalesce((SELECT a.enabled FROM beta.authority a),false),
 EXISTS(SELECT FROM pg_locks WHERE locktype='advisory' AND database=(SELECT oid FROM pg_database WHERE datname=current_database()) AND granted AND classid=943821 AND objsubid=2 AND objid=1),
 EXISTS(SELECT FROM pg_locks WHERE locktype='advisory' AND database=(SELECT oid FROM pg_database WHERE datname=current_database()) AND granted AND classid=943821 AND objsubid=2 AND objid=2),
 (SELECT count(*) FROM beta.slot WHERE state='pending' AND due<=now()),
 (SELECT count(*) FROM beta.slot WHERE state='uncertain'),
 (SELECT count(*) FROM beta.ui_call WHERE state='uncertain' OR (state='reserved' AND reserved_at<now()-interval '2 minutes')),
 (SELECT coalesce(extract(epoch FROM now()-min(due))::bigint,0) FROM beta.slot WHERE state='pending' AND due<=now())
$$;
CREATE FUNCTION beta.claim_notice() RETURNS TABLE(slot_id bigint,token uuid,recipient bigint,title text,starts timestamptz)
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 RETURN QUERY SELECT c.slot_id,c.token,c.recipient,p.title,o.starts FROM beta.claim() c
 JOIN beta.slot s ON s.id=c.slot_id JOIN beta.occurrence o ON o.id=s.occurrence JOIN beta.proposal p ON p.id=o.rule;
END $$;
CREATE OR REPLACE FUNCTION beta.fence_restore() RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 UPDATE beta.authority SET enabled=false,epoch=gen_random_uuid();
 UPDATE beta.proposal SET state='expired' WHERE state='pending';
 UPDATE beta.slot SET state='uncertain',lease=NULL,deadline=NULL WHERE state='sending';
 UPDATE beta.slot SET state='cancelled' WHERE state='pending';
 UPDATE beta.ui_call SET state='uncertain' WHERE state='reserved';
END $$;
REVOKE ALL ON FUNCTION beta.health(),beta.claim_notice() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION beta.health() TO personal_operator;
GRANT EXECUTE ON FUNCTION beta.claim_notice() TO personal_worker;
COMMIT;
