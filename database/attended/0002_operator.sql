BEGIN;
DO $$ BEGIN
 IF current_database()<>'dincharya_attended_test' OR current_setting('server_version_num')::int/10000<>17
 THEN RAISE EXCEPTION 'Disposable PG17 required'; END IF;
END $$;
SET LOCAL ROLE attended_executor;
ALTER TABLE attended.attempt ALTER COLUMN proposal DROP NOT NULL;
ALTER TABLE attended.attempt DROP CONSTRAINT attempt_kind_check;
ALTER TABLE attended.attempt ADD CHECK (
 (kind='historical' AND proposal IS NULL) OR
 (kind IN ('preview','decision','reminder') AND proposal IS NOT NULL)
);
CREATE UNIQUE INDEX single_history_reply ON attended.attempt(kind) WHERE kind='historical';
-- The bootstrap administrator copies the separately approved manifest digest here.
CREATE TABLE attended.operator_approval(
 singleton boolean PRIMARY KEY CHECK(singleton),
 digest text NOT NULL CHECK(digest ~ '^[0-9a-f]{64}$'),
 consumed boolean NOT NULL DEFAULT false
);
CREATE FUNCTION attended.start_operator(pin text,actor bigint,bot bigint,a timestamptz,b timestamptz)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE s attended.session;
BEGIN
 s:=attended.bound(actor,bot,'attended_poller');
 IF a IS DISTINCT FROM s.starts OR b IS DISTINCT FROM s.ends OR EXISTS(SELECT FROM attended.attempt)
 OR EXISTS(SELECT FROM attended.proposal) THEN RETURN false; END IF;
 UPDATE attended.operator_approval SET consumed=true WHERE singleton AND digest=pin AND NOT consumed;
 RETURN FOUND;
END $$;
CREATE FUNCTION attended.remaining(actor bigint,bot bigint) RETURNS int LANGUAGE plpgsql
SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM attended.bound(actor,bot,'attended_poller');
 RETURN 6-(SELECT count(*)::int FROM attended.attempt);
END $$;
CREATE FUNCTION attended.history_ticket(actor bigint,bot bigint) RETURNS uuid LANGUAGE plpgsql
SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM attended.bound(actor,bot,'attended_poller');
 IF NOT EXISTS(SELECT FROM attended.operator_approval WHERE consumed) THEN RAISE EXCEPTION 'approval required'; END IF;
 RETURN attended.reserve(NULL,'historical');
END $$;
GRANT EXECUTE ON FUNCTION attended.start_operator(text,bigint,bigint,timestamptz,timestamptz),
 attended.remaining(bigint,bigint),attended.history_ticket(bigint,bigint) TO attended_poller;
COMMIT;
