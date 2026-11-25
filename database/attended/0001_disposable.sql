BEGIN;
DO $$ BEGIN
 IF current_database()<>'dincharya_attended_test' OR current_setting('server_version_num')::int/10000<>17
 THEN RAISE EXCEPTION 'Disposable PG17 required'; END IF;
END $$;
CREATE ROLE attended_executor NOLOGIN;
CREATE ROLE attended_poller NOLOGIN;
CREATE ROLE attended_worker NOLOGIN;
CREATE SCHEMA attended AUTHORIZATION attended_executor;
SET LOCAL ROLE attended_executor;
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
CREATE TABLE attended.session (
 singleton boolean PRIMARY KEY CHECK(singleton), owner_id bigint NOT NULL CHECK(owner_id>0 AND owner_id<>101),
 bot_id bigint NOT NULL CHECK(bot_id>0 AND bot_id<>owner_id), starts timestamptz NOT NULL,
 ends timestamptz NOT NULL CHECK(isfinite(ends) AND ends>starts AND ends-starts<=interval '1 hour'),
 enabled boolean NOT NULL DEFAULT false
);
CREATE TABLE attended.proposal (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), update_id bigint UNIQUE NOT NULL CHECK(update_id>0),
 title text NOT NULL CHECK(length(title) BETWEEN 1 AND 80), due timestamptz NOT NULL,
 remind boolean NOT NULL, expires timestamptz NOT NULL,
 state text NOT NULL DEFAULT 'preview' CHECK(state IN ('preview','confirmed','cancelled'))
);
CREATE UNIQUE INDEX one_active_scenario ON attended.proposal(remind) WHERE state<>'cancelled';
CREATE UNIQUE INDEX one_confirmed_start ON attended.proposal(due) WHERE state='confirmed';
CREATE TABLE attended.attempt (
 ordinal int PRIMARY KEY CHECK(ordinal BETWEEN 1 AND 6), proposal uuid NOT NULL REFERENCES attended.proposal,
 kind text NOT NULL CHECK(kind IN ('preview','decision','reminder')), token uuid UNIQUE NOT NULL DEFAULT gen_random_uuid(),
 status text NOT NULL DEFAULT 'reserved' CHECK(status IN ('reserved','in_flight','sent','uncertain')),
 chat bigint, message bigint, UNIQUE(proposal,kind), UNIQUE(chat,message),
 CHECK((status='sent' AND chat IS NOT NULL AND message IS NOT NULL AND message>0)
    OR (status<>'sent' AND chat IS NULL AND message IS NULL))
);
CREATE UNIQUE INDEX single_reserved ON attended.attempt(status) WHERE status='reserved';
-- Called on the same dedicated connection throughout an owner's lifetime.
CREATE FUNCTION attended.acquire() RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF session_user NOT IN ('attended_worker','attended_poller') OR NOT pg_try_advisory_lock(
   824633,CASE session_user WHEN 'attended_poller' THEN 1 ELSE 2 END) THEN RETURN false; END IF;
 -- Only the successor of the same exclusive role may fence an abandoned send.
 UPDATE attended.attempt SET status='uncertain' WHERE status IN ('reserved','in_flight')
 AND ((session_user='attended_worker')=(kind='reminder'));
 RETURN true;
END $$;
CREATE FUNCTION attended.bound(actor bigint,bot bigint,role_name text) RETURNS attended.session
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE s attended.session;
BEGIN
 SELECT * INTO STRICT s FROM attended.session FOR UPDATE;
 IF session_user<>role_name OR NOT EXISTS(SELECT FROM pg_locks WHERE pid=pg_backend_pid()
   AND locktype='advisory' AND granted AND classid=824633 AND objsubid=2
   AND objid=CASE role_name WHEN 'attended_poller' THEN 1 ELSE 2 END)
 OR actor IS DISTINCT FROM s.owner_id OR bot IS DISTINCT FROM s.bot_id OR NOT s.enabled
 OR clock_timestamp() NOT BETWEEN s.starts AND s.ends
 OR EXISTS(SELECT FROM attended.attempt WHERE status<>'sent') THEN RAISE EXCEPTION 'session fenced'; END IF;
 RETURN s;
END $$;
CREATE FUNCTION attended.reserve(p uuid,k text) RETURNS uuid LANGUAGE sql SET search_path=pg_catalog,pg_temp AS $$
 INSERT INTO attended.attempt(ordinal,proposal,kind)
 SELECT count(*)::int+1,p,k FROM attended.attempt RETURNING token
$$;
CREATE FUNCTION attended.preview(actor bigint,bot bigint,req bigint,label text,at_time timestamptz,notify boolean)
RETURNS TABLE(proposal uuid,reservation uuid) LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE s attended.session; p uuid;
BEGIN
 s:=attended.bound(actor,bot,'attended_poller');
 IF at_time<=clock_timestamp() OR at_time>=s.ends THEN RAISE EXCEPTION 'appointment outside window'; END IF;
 INSERT INTO attended.proposal(update_id,title,due,remind,expires) VALUES(req,label,at_time,notify,
 least(s.ends,at_time,clock_timestamp()+interval '15 minutes')) RETURNING id INTO p;
 RETURN QUERY SELECT p,attended.reserve(p,'preview');
END $$;
CREATE FUNCTION attended.decide(actor bigint,bot bigint,p uuid,origin bigint,accepted boolean)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM attended.bound(actor,bot,'attended_poller');
 IF accepted IS NULL OR NOT EXISTS(SELECT FROM attended.attempt WHERE proposal=p AND kind='preview'
 AND status='sent' AND chat=actor AND message=origin) THEN RAISE EXCEPTION 'invalid callback origin'; END IF;
 UPDATE attended.proposal SET state=CASE WHEN accepted THEN 'confirmed' ELSE 'cancelled' END
 WHERE id=p AND state='preview' AND expires>clock_timestamp();
 IF NOT FOUND THEN RAISE EXCEPTION 'closed preview'; END IF;
 RETURN attended.reserve(p,'decision');
END $$;
CREATE FUNCTION attended.due(actor bigint,bot bigint) RETURNS TABLE(label text,reservation uuid)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p attended.proposal;
BEGIN
 PERFORM attended.bound(actor,bot,'attended_worker');
 SELECT * INTO p FROM attended.proposal r WHERE state='confirmed' AND remind
 AND due BETWEEN clock_timestamp()-interval '1 minute' AND clock_timestamp()
 AND NOT EXISTS(SELECT FROM attended.attempt a WHERE a.proposal=r.id AND a.kind='reminder')
 ORDER BY due LIMIT 1;
 IF FOUND THEN RETURN QUERY SELECT p.title,attended.reserve(p.id,'reminder'); END IF;
END $$;
CREATE FUNCTION attended.begin_send(ticket uuid,actor bigint,bot bigint) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE s attended.session;
BEGIN
 SELECT * INTO STRICT s FROM attended.session FOR UPDATE;
 IF NOT s.enabled OR actor IS DISTINCT FROM s.owner_id OR bot IS DISTINCT FROM s.bot_id
 OR clock_timestamp() NOT BETWEEN s.starts AND s.ends THEN RETURN false; END IF;
 UPDATE attended.attempt SET status='in_flight' WHERE token=ticket AND status='reserved'
 AND ((session_user='attended_worker' AND kind='reminder') OR (session_user='attended_poller' AND kind<>'reminder'))
 AND EXISTS(SELECT FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='advisory' AND granted
 AND classid=824633 AND objsubid=2 AND objid=CASE session_user WHEN 'attended_worker' THEN 2 ELSE 1 END);
 RETURN FOUND;
END $$;
CREATE FUNCTION attended.finish(ticket uuid,destination bigint,msg bigint) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE owner_chat bigint;
BEGIN
 SELECT owner_id INTO STRICT owner_chat FROM attended.session FOR UPDATE;
 IF destination IS DISTINCT FROM owner_chat OR msg IS NULL OR msg<=0 THEN
   destination:=NULL; msg:=NULL;
 END IF;
 UPDATE attended.attempt SET status=CASE WHEN msg IS NULL THEN 'uncertain' ELSE 'sent' END,
 chat=destination,message=msg WHERE token=ticket AND status='in_flight' AND
 ((session_user='attended_worker' AND kind='reminder') OR (session_user='attended_poller' AND kind<>'reminder'));
 RETURN FOUND AND msg IS NOT NULL;
END $$;
GRANT USAGE ON SCHEMA attended TO attended_poller,attended_worker;
GRANT EXECUTE ON FUNCTION attended.acquire(),attended.begin_send(uuid,bigint,bigint),attended.finish(uuid,bigint,bigint) TO attended_poller,attended_worker;
GRANT EXECUTE ON FUNCTION attended.preview(bigint,bigint,bigint,text,timestamptz,boolean),
 attended.decide(bigint,bigint,uuid,bigint,boolean) TO attended_poller;
GRANT EXECUTE ON FUNCTION attended.due(bigint,bigint) TO attended_worker;
COMMIT;
