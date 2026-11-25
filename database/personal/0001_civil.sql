-- Fresh PG17 personal candidate. No owner, login or activation is seeded.
BEGIN;
DO $$ BEGIN
 IF current_database() <> 'dincharya_personal_candidate'
    OR current_setting('server_version_num')::int / 10000 <> 17 THEN
   RAISE EXCEPTION 'fresh PG17 candidate required';
 END IF;
END $$;
CREATE ROLE personal_gateway NOLOGIN;
CREATE ROLE personal_worker NOLOGIN;
CREATE ROLE personal_executor NOLOGIN;
CREATE ROLE personal_operator NOLOGIN;
REVOKE ALL ON DATABASE dincharya_personal_candidate FROM PUBLIC;
GRANT CONNECT ON DATABASE dincharya_personal_candidate TO personal_gateway,personal_worker,personal_operator;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA beta AUTHORIZATION personal_executor;
SET LOCAL ROLE personal_executor;
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
CREATE TABLE beta.authority (
 singleton boolean PRIMARY KEY CHECK(singleton), recipient bigint UNIQUE NOT NULL CHECK(recipient>0),
 bot bigint UNIQUE NOT NULL CHECK(bot>0 AND bot<>recipient),
 enabled boolean NOT NULL DEFAULT false,
 lookback interval NOT NULL CHECK(lookback>=interval '0 seconds' AND lookback<=interval '6 hours'),
 epoch uuid NOT NULL DEFAULT gen_random_uuid()
);
CREATE FUNCTION beta.owned(role_name name) RETURNS boolean LANGUAGE sql SET search_path=pg_catalog,pg_temp AS $$
 SELECT session_user=role_name AND EXISTS(SELECT FROM pg_locks WHERE pid=pg_backend_pid()
 AND locktype='advisory' AND granted AND classid=943821 AND objsubid=2
 AND objid=CASE role_name WHEN 'personal_gateway' THEN 1 WHEN 'personal_worker' THEN 2 END)
$$;
CREATE FUNCTION beta.acquire() RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF session_user NOT IN ('personal_gateway','personal_worker') OR NOT EXISTS(SELECT FROM beta.authority WHERE enabled)
 THEN RETURN false; END IF;
 RETURN pg_try_advisory_lock(943821,CASE session_user WHEN 'personal_gateway' THEN 1 ELSE 2 END);
END $$;
CREATE TABLE beta.proposal (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), request_id bigint UNIQUE NOT NULL CHECK(request_id>0),
 epoch uuid NOT NULL, expires timestamptz NOT NULL, title text NOT NULL CHECK(length(title) BETWEEN 1 AND 80),
 frequency text NOT NULL CHECK(frequency IN ('once','daily','weekly','yearly')),
 starts date NOT NULL CHECK(isfinite(starts)), at_time time NOT NULL CHECK(at_time<'24:00'),
 offsets integer[] NOT NULL, revision integer NOT NULL DEFAULT 1, state text NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','active','paused','cancelled','expired'))
);
CREATE TABLE beta.occurrence (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, rule uuid NOT NULL REFERENCES beta.proposal,
 starts timestamptz NOT NULL, enabled boolean NOT NULL DEFAULT true, UNIQUE(rule,starts)
);
CREATE UNIQUE INDEX beta_active_start ON beta.occurrence(starts) WHERE enabled;
CREATE TABLE beta.slot (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, occurrence bigint NOT NULL REFERENCES beta.occurrence,
 minutes integer NOT NULL CHECK(minutes BETWEEN 0 AND 10080), due timestamptz NOT NULL,
 state text NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','sending','sent','uncertain','cancelled','dead')),
 attempts integer NOT NULL DEFAULT 0, retry_after timestamptz, lease uuid, deadline timestamptz, chat bigint, message bigint,
 UNIQUE(occurrence,minutes), UNIQUE(chat,message),
 FOREIGN KEY(chat) REFERENCES beta.authority(recipient),
 CHECK ((state='sent' AND chat IS NOT NULL AND message IS NOT NULL AND message>0)
        OR (state<>'sent' AND chat IS NULL AND message IS NULL)),
 CHECK ((lease IS NOT NULL)=(state='sending') AND (deadline IS NOT NULL)=(state='sending'))
);
CREATE FUNCTION beta.draft(actor bigint, req bigint, title_arg text, freq text, day date, tod time, offs integer[])
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p beta.proposal; a beta.authority;
BEGIN
 SELECT * INTO STRICT a FROM beta.authority FOR SHARE;
 IF actor IS DISTINCT FROM a.recipient OR offs IS NULL OR cardinality(offs)>9
    OR (cardinality(offs)>0 AND array_ndims(offs) IS DISTINCT FROM 1)
    OR EXISTS(SELECT 1 FROM unnest(offs) x WHERE x IS NULL OR x NOT BETWEEN 0 AND 10080)
    OR cardinality(offs)<>(SELECT count(DISTINCT x) FROM unnest(offs) x)
 THEN RAISE EXCEPTION 'invalid owner or offsets'; END IF;
 INSERT INTO beta.proposal(request_id,epoch,expires,title,frequency,starts,at_time,offsets)
 VALUES(req,a.epoch,now()+interval '15 minutes',title_arg,freq,day,tod,offs)
 ON CONFLICT(request_id) DO NOTHING;
 SELECT * INTO STRICT p FROM beta.proposal WHERE request_id=req;
 IF (p.epoch,p.title,p.frequency,p.starts,p.at_time,p.offsets) IS DISTINCT FROM
    (a.epoch,title_arg,freq,day,tod,offs) THEN RAISE EXCEPTION 'request mismatch'; END IF;
 RETURN p.id;
END $$;
-- Internal-only projector. Unique start times fail the complete transaction on a conflict.
CREATE FUNCTION beta.project(p beta.proposal) RETURNS void LANGUAGE sql
SET search_path=pg_catalog,pg_temp AS $$
 WITH dates AS (
 SELECT d::date AS day FROM generate_series(
 greatest(p.starts,(now() AT TIME ZONE 'Asia/Kolkata')::date)::timestamp,
 ((now() AT TIME ZONE 'Asia/Kolkata')::date+400)::timestamp,interval '1 day') d
 ), eligible AS (
 SELECT (day+p.at_time) AT TIME ZONE 'Asia/Kolkata' AS starts FROM dates
 WHERE p.frequency='daily' OR day=p.starts
 OR (p.frequency='weekly' AND (day-p.starts)%7=0)
 OR (p.frequency='yearly' AND to_char(day,'MM-DD')=to_char(p.starts,'MM-DD'))
 ), fresh AS (
 INSERT INTO beta.occurrence(rule,starts) SELECT p.id,starts FROM eligible WHERE starts>now()
 ON CONFLICT(rule,starts) DO NOTHING RETURNING id,starts
 )
 INSERT INTO beta.slot(occurrence,minutes,due)
 SELECT id,x,starts-x*interval '1 minute' FROM fresh CROSS JOIN unnest(p.offsets) x
 WHERE starts-x*interval '1 minute'>now();
$$;
CREATE FUNCTION beta.decide(actor bigint, token uuid, confirm boolean) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE a beta.authority; p beta.proposal;
BEGIN
 SELECT * INTO STRICT a FROM beta.authority FOR SHARE;
 SELECT * INTO STRICT p FROM beta.proposal WHERE id=token FOR UPDATE;
 IF actor IS DISTINCT FROM a.recipient OR a.epoch<>p.epoch OR confirm IS NULL THEN RAISE EXCEPTION 'invalid review'; END IF;
 IF p.state<>'pending' THEN RETURN p.state; END IF;
 IF p.expires<=clock_timestamp() THEN p.state:='expired';
 ELSIF confirm THEN
   IF (p.starts+p.at_time) AT TIME ZONE 'Asia/Kolkata' <= now() THEN RAISE EXCEPTION 'stale preview'; END IF;
   PERFORM beta.project(p); p.state:='active';
 ELSE p.state:='cancelled'; END IF;
 UPDATE beta.proposal SET state=p.state WHERE id=p.id;
 RETURN p.state;
END $$;
CREATE TABLE beta.change_review (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), request_id bigint UNIQUE NOT NULL CHECK(request_id>0), rule uuid NOT NULL REFERENCES beta.proposal,
 revision integer NOT NULL, epoch uuid NOT NULL, expires timestamptz NOT NULL,
 action text NOT NULL CHECK(action IN ('pause','resume','cancel')), result text
);
CREATE FUNCTION beta.review_change(actor bigint, req bigint, target uuid, action_arg text) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE a beta.authority; p beta.proposal; receipt uuid;
BEGIN
 SELECT * INTO STRICT a FROM beta.authority FOR SHARE;
 SELECT * INTO STRICT p FROM beta.proposal WHERE id=target FOR SHARE;
 IF actor IS DISTINCT FROM a.recipient OR p.epoch<>a.epoch OR
    NOT ((p.state='active' AND action_arg IN ('pause','cancel')) OR
         (p.state='paused' AND action_arg IN ('resume','cancel'))) THEN RAISE EXCEPTION 'invalid change'; END IF;
 INSERT INTO beta.change_review(request_id,rule,revision,epoch,expires,action)
 VALUES(req,target,p.revision,a.epoch,now()+interval '15 minutes',action_arg) ON CONFLICT(request_id) DO NOTHING;
 SELECT id INTO STRICT receipt FROM beta.change_review WHERE request_id=req AND rule=target
 AND revision=p.revision AND epoch=a.epoch AND action=action_arg;
 RETURN receipt;
END $$;
CREATE FUNCTION beta.apply_change(actor bigint, token uuid) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE a beta.authority; c beta.change_review; p beta.proposal;
BEGIN
 PERFORM pg_advisory_xact_lock(18890421);
 SELECT * INTO STRICT a FROM beta.authority FOR SHARE;
 SELECT * INTO STRICT c FROM beta.change_review WHERE id=token FOR UPDATE;
 IF actor IS DISTINCT FROM a.recipient OR a.epoch<>c.epoch THEN RAISE EXCEPTION 'invalid owner or epoch'; END IF;
 IF c.result IS NOT NULL THEN RETURN c.result; END IF;
 SELECT * INTO STRICT p FROM beta.proposal WHERE id=c.rule FOR UPDATE;
 IF c.revision<>p.revision OR c.expires<=clock_timestamp() THEN RAISE EXCEPTION 'stale change'; END IF;
 p.state:=CASE c.action WHEN 'pause' THEN 'paused' WHEN 'cancel' THEN 'cancelled' ELSE 'active' END;
 IF EXISTS(SELECT 1 FROM beta.slot s JOIN beta.occurrence o ON o.id=s.occurrence
           WHERE o.rule=p.id AND s.state='sending') THEN RAISE EXCEPTION 'delivery in progress'; END IF;
 UPDATE beta.occurrence SET enabled=(p.state='active') WHERE rule=p.id AND starts>now();
 IF p.state='active' THEN
   UPDATE beta.slot s SET state='pending' FROM beta.occurrence o
    WHERE s.occurrence=o.id AND o.rule=p.id AND s.state='cancelled' AND s.due>now();
   PERFORM beta.project(p);
 ELSE
   UPDATE beta.slot s SET state='cancelled' FROM beta.occurrence o
    WHERE s.occurrence=o.id AND o.rule=p.id AND s.state='pending';
 END IF;
 UPDATE beta.proposal SET state=p.state,revision=revision+1 WHERE id=p.id;
 UPDATE beta.change_review SET result=p.state WHERE id=c.id;
 RETURN p.state;
END $$;
CREATE FUNCTION beta.roll_forward() RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p beta.proposal;
BEGIN
 IF NOT beta.owned('personal_worker') OR NOT EXISTS(SELECT FROM beta.authority WHERE enabled FOR SHARE) THEN RAISE EXCEPTION 'worker fenced'; END IF;
 FOR p IN SELECT r.* FROM beta.proposal r JOIN beta.authority a ON a.epoch=r.epoch
          WHERE r.state='active' ORDER BY r.id FOR UPDATE OF r LOOP
   PERFORM beta.project(p);
 END LOOP;
END $$;
CREATE FUNCTION beta.claim() RETURNS TABLE(slot_id bigint,token uuid,recipient bigint)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE a beta.authority;
BEGIN
 IF NOT beta.owned('personal_worker') THEN RAISE EXCEPTION 'worker fenced'; END IF;
 SELECT * INTO STRICT a FROM beta.authority WHERE enabled FOR SHARE;
 PERFORM pg_advisory_xact_lock(18890421);
 UPDATE beta.slot SET state='uncertain',lease=NULL,deadline=NULL WHERE state='sending' AND deadline<=clock_timestamp();
 UPDATE beta.slot SET state='cancelled' WHERE state='pending' AND due<now()-a.lookback;
 IF EXISTS(SELECT 1 FROM beta.slot WHERE state='sending') THEN RETURN; END IF;
 RETURN QUERY WITH picked AS (
 SELECT s.id FROM beta.slot s WHERE s.state='pending' AND s.due<=now() AND (s.retry_after IS NULL OR s.retry_after<=now()) ORDER BY s.due,s.id
 LIMIT 1 FOR UPDATE SKIP LOCKED)
 UPDATE beta.slot s SET state='sending',attempts=attempts+1,lease=gen_random_uuid(),deadline=clock_timestamp()+interval '2 minutes'
 FROM picked WHERE s.id=picked.id RETURNING s.id,s.lease,a.recipient;
END $$;
CREATE TABLE beta.attempt (
 token uuid PRIMARY KEY, slot_id bigint NOT NULL REFERENCES beta.slot,
 at timestamptz NOT NULL DEFAULT clock_timestamp(), outcome text NOT NULL,chat bigint,message bigint
);
CREATE FUNCTION beta.log_attempt() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 INSERT INTO beta.attempt(token,slot_id,outcome,chat,message)
 VALUES(OLD.lease,OLD.id,NEW.state,NEW.chat,NEW.message);
 RETURN NEW;
END $$;
CREATE TRIGGER log_closed_attempt AFTER UPDATE ON beta.slot FOR EACH ROW
 WHEN (OLD.state='sending' AND NEW.state<>'sending') EXECUTE FUNCTION beta.log_attempt();
CREATE FUNCTION beta.finish(slot_id bigint,token uuid,result text,chat_id bigint,message_id bigint)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF NOT beta.owned('personal_worker') THEN RAISE EXCEPTION 'worker fenced'; END IF;
 IF result IS NULL OR result NOT IN ('sent','uncertain','not_accepted') THEN RAISE EXCEPTION 'invalid outcome'; END IF;
 UPDATE beta.slot SET state=CASE WHEN result='not_accepted' THEN
   CASE WHEN attempts>=5 THEN 'dead' ELSE 'pending' END ELSE result END,
 retry_after=CASE WHEN result='not_accepted' THEN now()+make_interval(secs=>30*(1<<(attempts-1))) END,chat=chat_id,message=message_id,lease=NULL,deadline=NULL
 WHERE id=slot_id AND lease=token AND state='sending' AND deadline>clock_timestamp();
 RETURN FOUND;
END $$;
CREATE FUNCTION beta.fence_restore() RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 UPDATE beta.authority SET enabled=false,epoch=gen_random_uuid();
 UPDATE beta.proposal SET state='expired' WHERE state='pending';
 UPDATE beta.slot SET state='uncertain',lease=NULL,deadline=NULL WHERE state='sending';
 UPDATE beta.slot SET state='cancelled' WHERE state='pending';
END $$;
-- Only an independently authorized operator may attach a confirmed paired receipt.
CREATE TABLE beta.receipt_evidence (
 id uuid PRIMARY KEY, epoch uuid NOT NULL, slot_id bigint NOT NULL REFERENCES beta.slot,
 chat bigint NOT NULL REFERENCES beta.authority(recipient), message bigint NOT NULL CHECK(message>0),
 digest text NOT NULL CHECK(digest ~ '^[0-9a-f]{64}$'),
 delivered_at timestamptz NOT NULL CHECK(isfinite(delivered_at)), verified boolean NOT NULL,
 issuer name NOT NULL DEFAULT session_user
);
CREATE TABLE beta.reconcile_permit (
 id uuid PRIMARY KEY, action_id uuid UNIQUE NOT NULL, operator_oid oid NOT NULL,
 epoch uuid NOT NULL, slot_id bigint NOT NULL REFERENCES beta.slot,
 evidence uuid NOT NULL REFERENCES beta.receipt_evidence, observed text NOT NULL CHECK(observed ~ '^[0-9a-f]{64}$'),
 reason text NOT NULL, approved boolean NOT NULL, expires timestamptz NOT NULL CHECK(isfinite(expires)),
 issuer name NOT NULL DEFAULT session_user
);
CREATE TABLE beta.resolution (
 action_id uuid PRIMARY KEY, slot_id bigint UNIQUE NOT NULL REFERENCES beta.slot,
 epoch uuid NOT NULL, evidence uuid NOT NULL REFERENCES beta.receipt_evidence, permit_id uuid UNIQUE NOT NULL REFERENCES beta.reconcile_permit,
 operator_oid oid NOT NULL,
 reason text NOT NULL CHECK(length(trim(reason)) BETWEEN 1 AND 500 AND reason !~ '[[:cntrl:]]'),
 observed text NOT NULL, chat bigint NOT NULL REFERENCES beta.authority(recipient), message bigint NOT NULL CHECK(message>0)
);
CREATE FUNCTION beta.reject_history_change() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,pg_temp AS $$ BEGIN RAISE EXCEPTION 'immutable reconciliation history'; END $$;
CREATE TRIGGER immutable_evidence BEFORE UPDATE OR DELETE OR TRUNCATE ON beta.receipt_evidence
 FOR EACH STATEMENT EXECUTE FUNCTION beta.reject_history_change();
CREATE TRIGGER immutable_permit BEFORE UPDATE OR DELETE OR TRUNCATE ON beta.reconcile_permit
 FOR EACH STATEMENT EXECUTE FUNCTION beta.reject_history_change();
CREATE TRIGGER immutable_resolution BEFORE UPDATE OR DELETE OR TRUNCATE ON beta.resolution
 FOR EACH STATEMENT EXECUTE FUNCTION beta.reject_history_change();
CREATE FUNCTION beta.inspect_uncertain() RETURNS TABLE(slot_id bigint,observation text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT s.id,encode(sha256(convert_to(a.epoch::text||'/'||s.id::text||'/'||s.attempts::text||'/'||t.token::text,'UTF8')),'hex')
 FROM beta.slot s JOIN beta.attempt t ON t.slot_id=s.id AND t.outcome='uncertain'
 CROSS JOIN beta.authority a WHERE s.state='uncertain';
$$;
CREATE FUNCTION beta.reconcile(action uuid,target bigint,observation_arg text,chat_id bigint,message_id bigint,
 evidence_id uuid,authorization_id uuid,reason_arg text,confirmed boolean) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE a beta.authority; r beta.resolution;
BEGIN
 IF session_user<>'personal_operator' OR confirmed IS DISTINCT FROM true THEN RAISE EXCEPTION 'operator confirmation required'; END IF;
 SELECT * INTO STRICT a FROM beta.authority FOR SHARE;
 PERFORM 1 FROM beta.slot WHERE id=target FOR UPDATE;
 SELECT * INTO r FROM beta.resolution WHERE action_id=action;
 IF FOUND THEN
   IF r.operator_oid IS DISTINCT FROM session_user::regrole::oid OR (r.epoch,r.slot_id,r.observed,r.chat,r.message,r.evidence,r.permit_id,r.reason)
      IS DISTINCT FROM (a.epoch,target,observation_arg,chat_id,message_id,evidence_id,authorization_id,reason_arg)
   THEN RAISE EXCEPTION 'reconciliation replay mismatch'; END IF;
   RETURN false;
 END IF;
 IF NOT EXISTS(SELECT FROM beta.inspect_uncertain() WHERE slot_id=target AND observation=observation_arg)
 THEN RAISE EXCEPTION 'stale observation'; END IF;
 -- Check after acquiring both locks, including expiry after any lock wait.
 IF NOT EXISTS (
   SELECT FROM beta.reconcile_permit p JOIN beta.receipt_evidence e ON e.id=p.evidence
   WHERE p.id=authorization_id AND p.action_id=action AND p.operator_oid=session_user::regrole::oid
     AND p.approved AND p.epoch=a.epoch AND p.slot_id=target AND p.observed=observation_arg
     AND p.reason=reason_arg AND p.expires>clock_timestamp()
     AND e.id=evidence_id AND e.verified AND e.epoch=a.epoch AND e.slot_id=target
     AND e.chat=a.recipient AND e.chat=chat_id AND e.message=message_id
     AND e.delivered_at<=clock_timestamp()
 ) THEN RAISE EXCEPTION 'invalid reconciliation authority' USING ERRCODE='42501'; END IF;
 INSERT INTO beta.resolution VALUES(action,target,a.epoch,evidence_id,authorization_id,session_user::regrole::oid,reason_arg,observation_arg,chat_id,message_id);
 UPDATE beta.slot SET state='sent',chat=chat_id,message=message_id WHERE id=target AND state='uncertain';
 RETURN true;
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA beta FROM PUBLIC;
GRANT EXECUTE ON FUNCTION beta.acquire() TO personal_gateway,personal_worker;
GRANT USAGE ON SCHEMA beta TO personal_gateway,personal_worker,personal_operator;
GRANT EXECUTE ON FUNCTION beta.inspect_uncertain(),beta.reconcile(uuid,bigint,text,bigint,bigint,uuid,uuid,text,boolean) TO personal_operator;
GRANT EXECUTE ON FUNCTION beta.roll_forward(),beta.claim(),beta.finish(bigint,uuid,text,bigint,bigint) TO personal_worker;
COMMIT;
