BEGIN;
DO $$ BEGIN
 IF current_database()<>'dincharya_personal_candidate' OR current_setting('server_version_num')::int/10000<>17
 THEN RAISE EXCEPTION 'personal PG17 required'; END IF;
END $$;
CREATE ROLE personal_observer NOLOGIN;
CREATE ROLE personal_backup NOLOGIN;
GRANT CONNECT ON DATABASE dincharya_personal_candidate TO personal_observer,personal_backup;
SET LOCAL ROLE personal_executor;
GRANT USAGE ON SCHEMA beta TO personal_observer,personal_backup;
GRANT EXECUTE ON FUNCTION beta.health() TO personal_observer;
CREATE TABLE beta.live_release(
 epoch uuid PRIMARY KEY, digest text NOT NULL UNIQUE CHECK(digest ~ '^[0-9a-f]{64}$'),
 profile text NOT NULL CHECK(profile IN ('bounded','daily')), opens timestamptz NOT NULL,
 closes timestamptz NOT NULL CHECK(closes>opens), started boolean NOT NULL DEFAULT false,
 attempts integer NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 6),
 reminders integer NOT NULL DEFAULT 0 CHECK(reminders BETWEEN 0 AND 1),
 cursor_id bigint NOT NULL DEFAULT 0,
 CHECK(profile='daily' OR closes-opens<=interval '1 hour')
);
-- Owner provisioning is external. Runtime identities have no table access.
CREATE FUNCTION beta.live_gate(actor bigint, bot_id bigint, pin text, mode text, op text, next_id bigint DEFAULT NULL)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE ep uuid; r beta.live_release;
BEGIN
 ep:=beta.ui_owner(actor,bot_id);
 SELECT * INTO STRICT r FROM beta.live_release WHERE epoch=ep AND digest=pin AND profile=mode FOR UPDATE;
 IF NOT (clock_timestamp()>=r.opens AND clock_timestamp()<r.closes)
 THEN RAISE EXCEPTION 'release window closed'; END IF;
 IF op='start' THEN
   IF mode='bounded' AND (r.started OR EXISTS(SELECT FROM beta.proposal) OR EXISTS(SELECT FROM beta.ui_call))
   THEN RAISE EXCEPTION 'fresh bounded fixture required'; END IF;
   UPDATE beta.live_release SET started=true WHERE epoch=ep;
 ELSIF NOT r.started THEN RAISE EXCEPTION 'release disabled';
 ELSIF op='ack' AND next_id>=r.cursor_id AND next_id>0 THEN
   UPDATE beta.live_release SET cursor_id=next_id WHERE epoch=ep;
 ELSIF op IN ('sendMessage','editMessageText','answerCallbackQuery','reminder') THEN
   IF mode='bounded' THEN
     IF r.attempts>=6 OR (op='reminder' AND r.reminders>=1) THEN RAISE EXCEPTION 'budget exhausted'; END IF;
     UPDATE beta.live_release SET attempts=attempts+1,reminders=reminders+(op='reminder')::int WHERE epoch=ep;
   END IF;
 ELSIF op IS DISTINCT FROM 'check' THEN RAISE EXCEPTION 'invalid release operation';
 END IF;
 IF op='check' AND mode='bounded' AND r.attempts>=6 THEN RETURN -1; END IF;
 RETURN r.cursor_id;
END $$;
REVOKE ALL ON FUNCTION beta.live_gate(bigint,bigint,text,text,text,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION beta.live_gate(bigint,bigint,text,text,text,bigint) TO personal_gateway;
ALTER TABLE beta.ui_call DROP CONSTRAINT ui_call_state_check;
ALTER TABLE beta.ui_call ADD CONSTRAINT ui_call_state_check CHECK(state IN ('reserved','received','uncertain','expired_callback'));
CREATE FUNCTION beta.expire_callback(actor bigint,bot_id bigint,ticket uuid) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE ep uuid;
BEGIN
 ep:=beta.ui_owner(actor,bot_id);
 UPDATE beta.ui_call SET state='expired_callback' WHERE id=ticket AND epoch=ep AND method='answerCallbackQuery' AND state='reserved';
 RETURN FOUND;
END $$;
REVOKE ALL ON FUNCTION beta.expire_callback(bigint,bigint,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION beta.expire_callback(bigint,bigint,uuid) TO personal_gateway;
GRANT SELECT ON ALL TABLES IN SCHEMA beta TO personal_backup;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA beta TO personal_backup;
COMMIT;
