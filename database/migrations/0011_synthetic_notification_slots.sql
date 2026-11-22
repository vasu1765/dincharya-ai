-- Isolated development. Preserve the legacy event/date ledger and its constraints.
DO $$ BEGIN
 IF current_database()<>'dincharya_app_test' OR session_user<>'synthetic_test' THEN
  RAISE EXCEPTION 'Isolated synthetic setup required';
 END IF;
END $$;

CREATE FUNCTION lunar_private.valid_offsets(p_offsets integer[]) RETURNS boolean
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT p_offsets IS NOT NULL AND cardinality(p_offsets)<=9
 AND NOT EXISTS (SELECT FROM unnest(p_offsets) x WHERE x IS NULL OR x NOT BETWEEN 0 AND 10080)
 AND cardinality(p_offsets)=(SELECT count(DISTINCT x) FROM unnest(p_offsets) x)
$$;

CREATE TABLE lunar_private.notification_policy (
 event_id bigint PRIMARY KEY REFERENCES public.schedule_events,
 offsets integer[] NOT NULL CHECK(lunar_private.valid_offsets(offsets)),
 effective_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE lunar_private.notification_slot (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 event_id bigint NOT NULL REFERENCES public.schedule_events,
 occurrence_date date NOT NULL,
 offset_minutes integer NOT NULL CHECK(offset_minutes BETWEEN 0 AND 10080),
 due_at timestamptz NOT NULL,
 payload jsonb NOT NULL,
 status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','failed','sending','sent','uncertain','dead','cancelled')),
 attempts integer NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 5),
 retry_at timestamptz,
 lease_until timestamptz,
 worker_token uuid,
 telegram_chat_id bigint,
 telegram_message_id bigint,
 UNIQUE(event_id,occurrence_date,offset_minutes),
 UNIQUE(telegram_chat_id,telegram_message_id),
 CHECK ((worker_token IS NOT NULL AND lease_until IS NOT NULL)=(status='sending')),
 CHECK ((telegram_chat_id IS NULL)=(telegram_message_id IS NULL)),
 CHECK(telegram_chat_id IS NULL OR (telegram_chat_id<>0 AND telegram_message_id>0 AND status='sent'))
);
CREATE INDEX notification_slot_claim ON lunar_private.notification_slot(due_at,id) WHERE status IN ('pending','failed');

CREATE FUNCTION lunar_private.set_notification_policy(p_event bigint,p_offsets integer[]) RETURNS void
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 IF NOT lunar_private.valid_offsets(p_offsets) THEN RAISE EXCEPTION 'Invalid notification offsets'; END IF;
 IF EXISTS(SELECT FROM public.reminder_deliveries WHERE event_id=p_event AND status='sending')
 OR EXISTS(SELECT FROM lunar_private.notification_slot WHERE event_id=p_event AND status='sending') THEN
  RAISE EXCEPTION 'Notification send in flight';
 END IF;
 INSERT INTO lunar_private.notification_policy(event_id,offsets) VALUES(p_event,p_offsets)
 ON CONFLICT(event_id) DO UPDATE SET offsets=excluded.offsets,effective_at=excluded.effective_at
 WHERE notification_policy.offsets IS DISTINCT FROM excluded.offsets;
 UPDATE public.reminder_deliveries SET status='cancelled' WHERE event_id=p_event AND managed_by='m2e'
 AND status IN ('pending','failed');
 UPDATE lunar_private.notification_slot SET status='cancelled' WHERE event_id=p_event
 AND status IN ('pending','failed') AND NOT offset_minutes=ANY(p_offsets);
END $$;

-- Legacy routines may still materialize their old queue. Intercept only new
-- m2e rows for explicitly opted-in events, without changing old uniqueness.
CREATE FUNCTION lunar_private.disable_legacy_notifications() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 IF NEW.managed_by='m2e' AND EXISTS(SELECT FROM lunar_private.notification_policy WHERE event_id=NEW.event_id) THEN
  RETURN NULL;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER disable_legacy_notifications BEFORE INSERT ON public.reminder_deliveries
 FOR EACH ROW EXECUTE FUNCTION lunar_private.disable_legacy_notifications();

CREATE FUNCTION lunar_private.guard_slot_send() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE target bigint;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 IF TG_TABLE_NAME='schedule_events' THEN target:=OLD.id;
 ELSIF TG_OP='DELETE' THEN target:=OLD.event_id;
 ELSE target:=NEW.event_id; END IF;
 IF EXISTS(SELECT FROM lunar_private.notification_slot WHERE event_id=target AND status='sending') THEN
  RAISE EXCEPTION 'Notification send in flight';
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER guard_notification_event BEFORE UPDATE OR DELETE ON public.schedule_events
 FOR EACH ROW EXECUTE FUNCTION lunar_private.guard_slot_send();
CREATE TRIGGER guard_notification_rule BEFORE UPDATE OR DELETE ON public.recurrence_rules
 FOR EACH ROW EXECUTE FUNCTION lunar_private.guard_slot_send();
CREATE TRIGGER guard_notification_override BEFORE INSERT OR UPDATE OR DELETE ON public.schedule_occurrence_overrides
 FOR EACH ROW EXECUTE FUNCTION lunar_private.guard_slot_send();

CREATE SCHEMA notification_worker_api;
REVOKE ALL ON SCHEMA notification_worker_api FROM PUBLIC;
GRANT USAGE ON SCHEMA notification_worker_api TO dincharya_reminder_worker;
GRANT SELECT ON lunar_private.notification_policy TO dincharya_worker_executor;
ALTER FUNCTION lunar_private.valid_offsets(integer[]) OWNER TO dincharya_lunar_executor;
REVOKE ALL ON FUNCTION lunar_private.valid_offsets(integer[]) FROM PUBLIC;
GRANT USAGE ON SCHEMA lunar_private TO dincharya_worker_executor;
GRANT SELECT,INSERT,UPDATE ON lunar_private.notification_slot TO dincharya_worker_executor;
GRANT USAGE ON SEQUENCE lunar_private.notification_slot_id_seq TO dincharya_worker_executor;
GRANT SELECT,INSERT,UPDATE ON lunar_private.notification_policy TO dincharya_lunar_executor;
GRANT SELECT ON lunar_private.notification_slot TO dincharya_lunar_executor;
GRANT UPDATE(status) ON lunar_private.notification_slot TO dincharya_lunar_executor;

CREATE FUNCTION notification_worker_api.claim_occurrence_reminders(p_now timestamptz,p_limit integer)
RETURNS TABLE(delivery_id bigint,worker_token uuid,payload jsonb)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF current_database()<>'dincharya_app_test' OR p_now IS NULL OR NOT isfinite(p_now)
 OR p_limit IS NULL OR p_limit NOT BETWEEN 1 AND 100 THEN RAISE EXCEPTION 'Invalid slot claim'; END IF;
 PERFORM pg_advisory_xact_lock(20261112,1);
 UPDATE lunar_private.notification_slot s SET status='uncertain',lease_until=NULL,worker_token=NULL
 WHERE s.status='sending' AND s.lease_until<=p_now;
 -- Cancel stale work before claiming. A cancelled appointment never gets a replacement slot.
 UPDATE lunar_private.notification_slot s SET status='cancelled'
 WHERE s.status IN ('pending','failed') AND (s.due_at<p_now-interval '6 hours' OR NOT EXISTS(
  SELECT FROM public.generate_event_occurrences(s.occurrence_date,s.occurrence_date) o
  JOIN lunar_private.notification_policy p ON p.event_id=o.event_id
  WHERE o.event_id=s.event_id AND s.offset_minutes=ANY(p.offsets)
   AND ((o.occurrence_date+o.start_time) AT TIME ZONE o.timezone)
       -make_interval(mins=>s.offset_minutes)=s.due_at));
 WITH desired AS (
  SELECT o.event_id,o.occurrence_date,n.offset_minutes,
    ((o.occurrence_date+o.start_time) AT TIME ZONE o.timezone)-make_interval(mins=>n.offset_minutes) AS due,
    p.effective_at,
    jsonb_build_object('event_id',o.event_id,'occurrence_date',o.occurrence_date,'title',o.event_title,
                       'start_time',o.start_time,'timezone',o.timezone,'offset_minutes',n.offset_minutes) AS body
  FROM public.generate_event_occurrences(
     ((p_now-interval '7 hours') AT TIME ZONE 'Asia/Kolkata')::date,
     ((p_now+interval '8 days') AT TIME ZONE 'Asia/Kolkata')::date) o
  JOIN lunar_private.notification_policy p ON p.event_id=o.event_id
  CROSS JOIN LATERAL unnest(p.offsets) n(offset_minutes)
 )
 INSERT INTO lunar_private.notification_slot AS s(event_id,occurrence_date,offset_minutes,due_at,payload,retry_at)
 SELECT event_id,occurrence_date,offset_minutes,due,body,due FROM desired
 WHERE due BETWEEN greatest(effective_at,p_now-interval '6 hours') AND p_now+interval '24 hours'
 AND NOT EXISTS(SELECT FROM public.reminder_deliveries d WHERE d.event_id=desired.event_id
  AND d.occurrence_date=desired.occurrence_date AND desired.offset_minutes=0
  AND (d.status IN ('sent','sending','uncertain','dead') OR d.managed_by IS DISTINCT FROM 'm2e'))
 ON CONFLICT(event_id,occurrence_date,offset_minutes) DO UPDATE
 SET status=CASE WHEN s.status='cancelled' THEN 'pending' ELSE s.status END,
     due_at=excluded.due_at,payload=excluded.payload,
     retry_at=CASE WHEN s.due_at<>excluded.due_at OR s.status='cancelled'
                THEN excluded.due_at ELSE s.retry_at END
 WHERE s.status IN ('pending','failed','cancelled') AND s.attempts<5;
 RETURN QUERY WITH ready AS (
  SELECT s.id FROM lunar_private.notification_slot s WHERE s.status IN ('pending','failed')
  AND s.attempts<5 AND s.due_at<=p_now AND s.retry_at<=p_now ORDER BY s.due_at,s.id FOR UPDATE SKIP LOCKED LIMIT p_limit
 )
 UPDATE lunar_private.notification_slot s SET status='sending',attempts=s.attempts+1,
   worker_token=gen_random_uuid(),lease_until=p_now+interval '2 minutes'
 FROM ready WHERE s.id=ready.id RETURNING s.id,s.worker_token,s.payload;
END $$;

CREATE FUNCTION notification_worker_api.acknowledge_occurrence_reminder(
 p_id bigint,p_token uuid,p_outcome text,p_now timestamptz,p_chat bigint,p_message bigint
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 IF current_database()<>'dincharya_app_test' OR p_now IS NULL OR NOT isfinite(p_now)
 OR p_outcome IS NULL OR p_outcome NOT IN ('sent','not_accepted','uncertain')
 OR (p_chat IS NULL)<>(p_message IS NULL)
 OR (p_chat IS NOT NULL AND (p_chat=0 OR p_message<=0 OR p_outcome<>'sent')) THEN
  RAISE EXCEPTION 'Invalid slot acknowledgement';
 END IF;
 UPDATE lunar_private.notification_slot s SET
  status=CASE p_outcome WHEN 'sent' THEN 'sent' WHEN 'uncertain' THEN 'uncertain'
          ELSE CASE WHEN s.attempts>=5 THEN 'dead' ELSE 'failed' END END,
  retry_at=CASE WHEN p_outcome='not_accepted' THEN p_now+make_interval(secs=>30*(1<<(s.attempts-1))) END,
  worker_token=NULL,lease_until=NULL,telegram_chat_id=p_chat,telegram_message_id=p_message
 WHERE s.id=p_id AND s.status='sending' AND s.worker_token=p_token AND s.lease_until>p_now;
 RETURN FOUND;
END $$;
CREATE FUNCTION notification_worker_api.finish_occurrence_reminder(
 p_id bigint,p_token uuid,p_outcome text,p_now timestamptz
) RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT notification_worker_api.acknowledge_occurrence_reminder(p_id,p_token,p_outcome,p_now,NULL,NULL)
$$;
GRANT USAGE ON SCHEMA notification_worker_api TO dincharya_worker_executor;
ALTER FUNCTION notification_worker_api.claim_occurrence_reminders(timestamptz,integer) OWNER TO dincharya_worker_executor;
ALTER FUNCTION notification_worker_api.acknowledge_occurrence_reminder(bigint,uuid,text,timestamptz,bigint,bigint) OWNER TO dincharya_worker_executor;
ALTER FUNCTION notification_worker_api.finish_occurrence_reminder(bigint,uuid,text,timestamptz) OWNER TO dincharya_worker_executor;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA notification_worker_api FROM PUBLIC;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA notification_worker_api TO dincharya_reminder_worker;
ALTER FUNCTION lunar_private.disable_legacy_notifications() OWNER TO dincharya_lunar_executor;
ALTER FUNCTION lunar_private.guard_slot_send() OWNER TO dincharya_lunar_executor;
REVOKE ALL ON FUNCTION lunar_private.disable_legacy_notifications(),lunar_private.guard_slot_send(),
 lunar_private.set_notification_policy(bigint,integer[]) FROM PUBLIC;
ALTER FUNCTION lunar_private.set_notification_policy(bigint,integer[]) OWNER TO dincharya_lunar_executor;
