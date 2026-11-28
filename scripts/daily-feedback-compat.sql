-- Optional compatibility rollback. Keep STOP in place and stop both runtime roles first.
BEGIN;
DO $$ BEGIN
 IF current_database()<>'dincharya_personal_candidate'
 OR to_regclass('beta.lunar_schedule') IS NULL
 OR EXISTS(SELECT FROM pg_stat_activity WHERE datname=current_database()
  AND usename IN ('personal_gateway','personal_worker'))
 OR EXISTS(SELECT FROM pg_locks WHERE locktype='advisory' AND classid=943821 AND objsubid=2
  AND database=(SELECT oid FROM pg_database WHERE datname=current_database()) AND granted)
 THEN RAISE EXCEPTION 'stopped personal 0006 target required'; END IF;
END $$;
SET LOCAL ROLE personal_executor;

CREATE OR REPLACE FUNCTION beta.roll_forward() RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p beta.proposal;
BEGIN
 IF NOT beta.owned('personal_worker') OR NOT EXISTS(SELECT FROM beta.authority WHERE enabled FOR SHARE) THEN RAISE EXCEPTION 'worker fenced'; END IF;
 FOR p IN SELECT r.* FROM beta.proposal r JOIN beta.authority a ON a.epoch=r.epoch
          WHERE r.state='active' ORDER BY r.id FOR UPDATE OF r LOOP
   PERFORM beta.project(p);
 END LOOP;
END $$;

CREATE OR REPLACE FUNCTION beta.ui_rules(actor bigint,bot_id bigint) RETURNS TABLE(id uuid,title text,frequency text)
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE ep uuid;
BEGIN
 ep:=beta.ui_owner(actor,bot_id);
 RETURN QUERY SELECT p.id,p.title,p.frequency FROM beta.proposal p WHERE p.epoch=ep AND p.state='active'
 ORDER BY p.starts,p.at_time,p.id LIMIT 25;
END $$;

COMMIT;
