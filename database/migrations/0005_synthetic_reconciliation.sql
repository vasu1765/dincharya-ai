-- Deliberately synthetic-only. This is not a production enablement migration.
DO $$ BEGIN
 IF current_database()<>'dincharya_app_test' OR session_user<>'synthetic_test' THEN
  RAISE EXCEPTION 'Isolated synthetic reconciliation setup required';
 END IF;
 IF EXISTS(SELECT FROM pg_roles WHERE rolname IN ('dincharya_reconcile_executor',
  'dincharya_reconcile_operator','dincharya_worker_executor','dincharya_reminder_worker')) THEN
  RAISE EXCEPTION 'Synthetic reconciliation roles already exist; explicit review required';
 END IF;
END $$;
CREATE ROLE dincharya_reconcile_executor NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE dincharya_reconcile_operator NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE dincharya_worker_executor NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE dincharya_reminder_worker NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE SCHEMA reconcile_private;
CREATE SCHEMA reconcile_api;
CREATE SCHEMA reminder_worker_api;
REVOKE ALL ON SCHEMA reconcile_private,reconcile_api,reminder_worker_api FROM PUBLIC;

CREATE TABLE reconcile_private.gate (
 singleton boolean PRIMARY KEY CHECK(singleton), enabled boolean NOT NULL DEFAULT false,
 environment text NOT NULL CHECK(environment='isolated_synthetic')
);
INSERT INTO reconcile_private.gate VALUES(true,false,'isolated_synthetic');
CREATE TABLE reconcile_private.operators (
 role_oid oid PRIMARY KEY, role_name name NOT NULL UNIQUE,
 destination bigint NOT NULL CHECK(destination>0), enabled boolean NOT NULL DEFAULT false
);
CREATE TABLE reconcile_private.delivery_destinations (
 delivery_id bigint PRIMARY KEY REFERENCES public.reminder_deliveries(id),
 chat_id bigint NOT NULL CHECK(chat_id>0),
 pinned_by name NOT NULL DEFAULT session_user, pinned_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
-- Trusted fixture administrator/evidence authority provisions these private,
-- immutable attestations and one-use permits. Operators cannot manufacture them.
CREATE TABLE reconcile_private.evidence (
 evidence_ref uuid PRIMARY KEY, delivery_id bigint NOT NULL REFERENCES public.reminder_deliveries(id),
 chat_id bigint NOT NULL CHECK(chat_id>0), message_id bigint NOT NULL CHECK(message_id>0),
 digest text NOT NULL CHECK(digest ~ '^[0-9a-f]{64}$'),
 delivered_at timestamptz NOT NULL CHECK(isfinite(delivered_at)), verified boolean NOT NULL,
 attested_by name NOT NULL DEFAULT session_user, attested_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE reconcile_private.authorizations (
 authorization_ref uuid PRIMARY KEY, action_id uuid NOT NULL UNIQUE,
 operator_oid oid NOT NULL REFERENCES reconcile_private.operators(role_oid),
 delivery_id bigint NOT NULL REFERENCES public.reminder_deliveries(id),
 evidence_ref uuid NOT NULL REFERENCES reconcile_private.evidence(evidence_ref),
 observation_version text NOT NULL CHECK(observation_version ~ '^[0-9a-f]{64}$'),
 reason text NOT NULL CHECK(length(btrim(reason)) BETWEEN 1 AND 500 AND reason !~ '[[:cntrl:]]'),
 approved boolean NOT NULL, expires_at timestamptz NOT NULL CHECK(isfinite(expires_at)),
 authorized_by name NOT NULL DEFAULT session_user, authorized_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE reconcile_private.audit (
 action_id uuid PRIMARY KEY, authorization_ref uuid NOT NULL UNIQUE REFERENCES reconcile_private.authorizations,
 delivery_id bigint NOT NULL UNIQUE REFERENCES public.reminder_deliveries(id),
 operator_oid oid NOT NULL, operator_name name NOT NULL,
 evidence_ref uuid NOT NULL REFERENCES reconcile_private.evidence,
 evidence_digest text NOT NULL, chat_id bigint NOT NULL, message_id bigint NOT NULL,
 reason text NOT NULL, action text NOT NULL CHECK(action='record_confirmed_delivered'),
 request_hash text NOT NULL, before_version text NOT NULL, after_version text NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE FUNCTION reconcile_private.immutable_record() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
 RAISE EXCEPTION 'Reconciliation records are append-only' USING ERRCODE='55000';
END $$;
CREATE TRIGGER immutable_audit BEFORE UPDATE OR DELETE ON reconcile_private.audit
 FOR EACH ROW EXECUTE FUNCTION reconcile_private.immutable_record();
CREATE TRIGGER immutable_audit_truncate BEFORE TRUNCATE ON reconcile_private.audit
 FOR EACH STATEMENT EXECUTE FUNCTION reconcile_private.immutable_record();
CREATE TRIGGER immutable_evidence BEFORE UPDATE OR DELETE ON reconcile_private.evidence
 FOR EACH ROW EXECUTE FUNCTION reconcile_private.immutable_record();
CREATE TRIGGER immutable_evidence_truncate BEFORE TRUNCATE ON reconcile_private.evidence
 FOR EACH STATEMENT EXECUTE FUNCTION reconcile_private.immutable_record();
CREATE TRIGGER immutable_destination BEFORE UPDATE OR DELETE ON reconcile_private.delivery_destinations
 FOR EACH ROW EXECUTE FUNCTION reconcile_private.immutable_record();
CREATE TRIGGER immutable_destination_truncate BEFORE TRUNCATE ON reconcile_private.delivery_destinations
 FOR EACH STATEMENT EXECUTE FUNCTION reconcile_private.immutable_record();
CREATE TRIGGER immutable_authorization BEFORE UPDATE OR DELETE ON reconcile_private.authorizations
 FOR EACH ROW EXECUTE FUNCTION reconcile_private.immutable_record();
CREATE TRIGGER immutable_authorization_truncate BEFORE TRUNCATE ON reconcile_private.authorizations
 FOR EACH STATEMENT EXECUTE FUNCTION reconcile_private.immutable_record();

GRANT USAGE ON SCHEMA reconcile_private,public TO dincharya_reconcile_executor;
GRANT SELECT ON reconcile_private.gate,reconcile_private.operators,reconcile_private.evidence,
 reconcile_private.delivery_destinations,reconcile_private.authorizations,reconcile_private.audit,
 public.reminder_deliveries TO dincharya_reconcile_executor;
-- These constant identity-column privileges permit FOR SHARE locks without
-- granting permission to change enablement, destination or operator identity names.
GRANT UPDATE(singleton) ON reconcile_private.gate TO dincharya_reconcile_executor;
GRANT UPDATE(role_oid) ON reconcile_private.operators TO dincharya_reconcile_executor;
GRANT UPDATE(status,sent_at,telegram_chat_id,telegram_message_id) ON public.reminder_deliveries
 TO dincharya_reconcile_executor;
GRANT INSERT ON reconcile_private.audit TO dincharya_reconcile_executor;

CREATE FUNCTION reconcile_api.inspect_uncertain(p_after_id bigint DEFAULT 0,p_limit integer DEFAULT 20)
RETURNS TABLE(delivery_id bigint,event_id bigint,occurrence_date date,attempts integer,
 due_at timestamptz,claimed_at timestamptz,observation_version text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET TimeZone='UTC' AS $$
BEGIN
 IF current_database()<>'dincharya_app_test'
  OR NOT EXISTS(SELECT FROM reconcile_private.gate WHERE enabled AND environment='isolated_synthetic')
  OR NOT pg_has_role(session_user,'dincharya_reconcile_operator','member')
  OR pg_has_role(session_user,'dincharya_reminder_worker','member')
  OR NOT EXISTS(SELECT FROM reconcile_private.operators o WHERE o.enabled
     AND o.role_name=session_user AND o.role_oid=to_regrole(session_user)::oid) THEN
  RAISE EXCEPTION 'Operator reconciliation unavailable or unauthorized' USING ERRCODE='42501';
 END IF;
 IF p_after_id IS NULL OR p_after_id<0 OR p_limit IS NULL OR p_limit NOT BETWEEN 1 AND 100 THEN
  RAISE EXCEPTION 'Invalid inspection bounds' USING ERRCODE='22023';
 END IF;
 RETURN QUERY SELECT d.id,d.event_id,d.occurrence_date,d.attempts,d.due_at,d.claimed_at,
  encode(sha256(convert_to(to_jsonb(d)::text,'UTF8')),'hex')
 FROM public.reminder_deliveries d WHERE d.managed_by='m2e' AND d.status='uncertain' AND d.id>p_after_id
 ORDER BY d.id LIMIT p_limit;
END $$;

CREATE FUNCTION reconcile_api.record_confirmed_delivered(p_action_id uuid,p_delivery_id bigint,
 p_observation_version text,p_chat_id bigint,p_message_id bigint,p_evidence_ref uuid,
 p_reason text,p_authorization_ref uuid,p_confirmed boolean)
RETURNS TABLE(success boolean,replayed boolean,code text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp SET TimeZone='UTC' AS $$
DECLARE principal reconcile_private.operators%ROWTYPE; permit reconcile_private.authorizations%ROWTYPE;
 proof reconcile_private.evidence%ROWTYPE; previous reconcile_private.audit%ROWTYPE;
 delivery public.reminder_deliveries%ROWTYPE; fingerprint text; request_hash text; before_version text;
BEGIN
 IF current_database()<>'dincharya_app_test'
  OR NOT pg_has_role(session_user,'dincharya_reconcile_operator','member')
  OR pg_has_role(session_user,'dincharya_reminder_worker','member') THEN
  RETURN QUERY SELECT false,false,'not_authorized'::text; RETURN;
 END IF;
 PERFORM pg_advisory_xact_lock(20261112,1);
 PERFORM FROM reconcile_private.gate WHERE enabled AND environment='isolated_synthetic' FOR SHARE;
 IF NOT FOUND THEN RETURN QUERY SELECT false,false,'disabled'::text; RETURN; END IF;
 SELECT * INTO principal FROM reconcile_private.operators o WHERE o.enabled AND o.role_name=session_user
  AND o.role_oid=to_regrole(session_user)::oid FOR SHARE;
 IF NOT FOUND THEN RETURN QUERY SELECT false,false,'not_authorized'::text; RETURN; END IF;
 IF p_confirmed IS DISTINCT FROM true OR p_action_id IS NULL OR p_delivery_id IS NULL
  OR p_observation_version IS NULL OR p_observation_version !~ '^[0-9a-f]{64}$'
  OR p_chat_id IS DISTINCT FROM principal.destination OR p_message_id IS NULL OR p_message_id<=0
  OR p_evidence_ref IS NULL OR p_authorization_ref IS NULL OR p_reason IS NULL
  OR length(btrim(p_reason)) NOT BETWEEN 1 AND 500 OR p_reason ~ '[[:cntrl:]]' THEN
  RETURN QUERY SELECT false,false,'invalid_request'::text; RETURN;
 END IF;
 request_hash:=encode(sha256(convert_to(jsonb_build_object('action',p_action_id,'delivery',p_delivery_id,
  'version',p_observation_version,'chat',p_chat_id,'message',p_message_id,'evidence',p_evidence_ref,
  'reason',p_reason,'authorization',p_authorization_ref,'operator',principal.role_oid)::text,'UTF8')),'hex');
 SELECT * INTO previous FROM reconcile_private.audit a WHERE a.action_id=p_action_id;
 IF FOUND THEN
  IF previous.operator_oid=principal.role_oid AND previous.request_hash=request_hash THEN
   RETURN QUERY SELECT true,true,'replayed'::text;
  ELSE RETURN QUERY SELECT false,false,'action_mismatch'::text; END IF;
  RETURN;
 END IF;
 SELECT * INTO permit FROM reconcile_private.authorizations a WHERE a.authorization_ref=p_authorization_ref
  AND a.approved AND a.action_id=p_action_id AND a.operator_oid=principal.role_oid
  AND a.delivery_id=p_delivery_id AND a.evidence_ref=p_evidence_ref
  AND a.observation_version=p_observation_version AND a.reason=p_reason AND a.expires_at>clock_timestamp();
 IF NOT FOUND THEN RETURN QUERY SELECT false,false,'authorization_invalid'::text; RETURN; END IF;
 IF NOT EXISTS(SELECT FROM reconcile_private.delivery_destinations q
   WHERE q.delivery_id=p_delivery_id AND q.chat_id=p_chat_id) THEN
  RETURN QUERY SELECT false,false,'destination_invalid'::text; RETURN;
 END IF;
 SELECT * INTO proof FROM reconcile_private.evidence e WHERE e.evidence_ref=p_evidence_ref AND e.verified
  AND e.delivery_id=p_delivery_id AND e.chat_id=p_chat_id AND e.message_id=p_message_id
  AND e.delivered_at<=clock_timestamp();
 IF NOT FOUND THEN RETURN QUERY SELECT false,false,'evidence_invalid'::text; RETURN; END IF;
 SELECT * INTO delivery FROM public.reminder_deliveries d WHERE d.id=p_delivery_id FOR UPDATE;
 -- A conflicting transaction can outlive the authorization while we wait.
 IF permit.expires_at<=clock_timestamp() THEN
  RETURN QUERY SELECT false,false,'authorization_invalid'::text; RETURN;
 END IF;
 IF NOT FOUND OR delivery.managed_by IS DISTINCT FROM 'm2e' OR delivery.status IS DISTINCT FROM 'uncertain'
  OR delivery.worker_token IS NOT NULL OR delivery.lease_until IS NOT NULL OR delivery.attempts<1
  OR delivery.claimed_at IS NULL OR proof.delivered_at<delivery.claimed_at
  OR delivery.telegram_chat_id IS NOT NULL OR delivery.telegram_message_id IS NOT NULL THEN
  RETURN QUERY SELECT false,false,'unavailable'::text; RETURN;
 END IF;
 before_version:=encode(sha256(convert_to(to_jsonb(delivery)::text,'UTF8')),'hex');
 IF before_version<>p_observation_version THEN
  RETURN QUERY SELECT false,false,'stale_observation'::text; RETURN;
 END IF;
 BEGIN
  UPDATE public.reminder_deliveries SET status='sent',sent_at=proof.delivered_at,
   telegram_chat_id=p_chat_id,telegram_message_id=p_message_id WHERE id=p_delivery_id RETURNING * INTO delivery;
  fingerprint:=encode(sha256(convert_to(to_jsonb(delivery)::text,'UTF8')),'hex');
  INSERT INTO reconcile_private.audit(action_id,authorization_ref,delivery_id,operator_oid,operator_name,
   evidence_ref,evidence_digest,chat_id,message_id,reason,action,request_hash,before_version,after_version)
  VALUES(p_action_id,p_authorization_ref,p_delivery_id,principal.role_oid,session_user,
   p_evidence_ref,proof.digest,p_chat_id,p_message_id,p_reason,'record_confirmed_delivered',
   request_hash,before_version,fingerprint);
 EXCEPTION WHEN unique_violation THEN
  RETURN QUERY SELECT false,false,'identity_conflict'::text; RETURN;
 WHEN OTHERS THEN
  RETURN QUERY SELECT false,false,'storage_failed'::text; RETURN;
 END;
 RETURN QUERY SELECT true,false,'recorded'::text;
END $$;
ALTER FUNCTION reconcile_api.inspect_uncertain(bigint,integer) OWNER TO dincharya_reconcile_executor;
ALTER FUNCTION reconcile_api.record_confirmed_delivered(uuid,bigint,text,bigint,bigint,uuid,text,uuid,boolean)
 OWNER TO dincharya_reconcile_executor;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA reconcile_api,reconcile_private FROM PUBLIC;
GRANT USAGE ON SCHEMA reconcile_api TO dincharya_reconcile_operator;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA reconcile_api TO dincharya_reconcile_operator;

-- Ordinary workers get only constrained lease APIs, not direct ledger writes,
-- audit/evidence/permit access or membership in the operator/executor roles.
GRANT USAGE ON SCHEMA public TO dincharya_worker_executor;
GRANT SELECT ON public.schedule_events,public.recurrence_rules,public.schedule_occurrence_overrides
 TO dincharya_worker_executor;
GRANT SELECT,INSERT,UPDATE ON public.reminder_deliveries TO dincharya_worker_executor;
DO $$ DECLARE sequence_name regclass; BEGIN
 sequence_name:=pg_get_serial_sequence('public.reminder_deliveries','id')::regclass;
 IF sequence_name IS NOT NULL THEN
  EXECUTE format('GRANT USAGE ON SEQUENCE %s TO dincharya_worker_executor',sequence_name);
 END IF;
END $$;
CREATE FUNCTION reminder_worker_api.claim_occurrence_reminders(p_now timestamptz DEFAULT now(),
 p_limit integer DEFAULT 20,p_lease interval DEFAULT interval '2 minutes')
RETURNS TABLE(delivery_id bigint,event_id bigint,occurrence_date date,payload jsonb,worker_token uuid,lease_until timestamptz)
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT * FROM public.claim_occurrence_reminders(p_now,p_limit,p_lease)
$$;
CREATE FUNCTION reminder_worker_api.finish_occurrence_reminder(p_id bigint,p_token uuid,p_outcome text,
 p_now timestamptz DEFAULT now()) RETURNS boolean
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT public.finish_occurrence_reminder(p_id,p_token,p_outcome,p_now)
$$;
CREATE FUNCTION reminder_worker_api.acknowledge_occurrence_reminder(p_id bigint,p_token uuid,p_outcome text,
 p_now timestamptz,p_chat bigint DEFAULT NULL,p_message bigint DEFAULT NULL) RETURNS boolean
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT public.acknowledge_occurrence_reminder(p_id,p_token,p_outcome,p_now,p_chat,p_message)
$$;
ALTER FUNCTION reminder_worker_api.claim_occurrence_reminders(timestamptz,integer,interval) OWNER TO dincharya_worker_executor;
ALTER FUNCTION reminder_worker_api.finish_occurrence_reminder(bigint,uuid,text,timestamptz) OWNER TO dincharya_worker_executor;
ALTER FUNCTION reminder_worker_api.acknowledge_occurrence_reminder(bigint,uuid,text,timestamptz,bigint,bigint) OWNER TO dincharya_worker_executor;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA reminder_worker_api FROM PUBLIC;
GRANT USAGE ON SCHEMA reminder_worker_api TO dincharya_reminder_worker;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA reminder_worker_api TO dincharya_reminder_worker;
