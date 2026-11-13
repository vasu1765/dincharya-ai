-- Retain legacy delivery rows and their event/date uniqueness. No external sends.
ALTER TABLE public.reminder_deliveries
 ADD COLUMN managed_by text,
 ADD COLUMN due_at timestamptz,
 ADD COLUMN payload jsonb,
 ADD COLUMN attempts integer NOT NULL DEFAULT 0,
 ADD COLUMN retry_at timestamptz,
 ADD COLUMN worker_token uuid,
 ADD COLUMN lease_until timestamptz;
ALTER TABLE public.reminder_deliveries DROP CONSTRAINT reminder_deliveries_status_check;
ALTER TABLE public.reminder_deliveries ADD CONSTRAINT reminder_deliveries_status_check
 CHECK (status IN ('pending','sent','failed','sending','cancelled','uncertain','dead'));
ALTER TABLE public.reminder_deliveries ADD CONSTRAINT reminder_attempts_nonnegative CHECK (attempts>=0);
CREATE INDEX reminder_due_queue ON public.reminder_deliveries(status,due_at,retry_at)
 WHERE managed_by='m2e';

CREATE FUNCTION public.refresh_occurrence_reminders(p_now timestamptz DEFAULT now(),
 p_lookback interval DEFAULT interval '6 hours',p_lookahead interval DEFAULT interval '24 hours')
RETURNS integer LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE affected integer;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 IF p_now IS NULL OR NOT isfinite(p_now) OR p_lookback IS NULL OR p_lookahead IS NULL
    OR p_lookback<interval '0' OR p_lookback>interval '7 days'
    OR p_lookahead<interval '0' OR p_lookahead>interval '7 days' THEN
    RAISE EXCEPTION 'Reminder window must be finite and at most seven days' USING ERRCODE='22023'; END IF;
 -- Expired send leases are ambiguous: never automatically replay a possibly accepted send.
 UPDATE public.reminder_deliveries SET status='uncertain',worker_token=NULL,lease_until=NULL,
    error_message='Send lease expired; operator reconciliation required'
 WHERE managed_by='m2e' AND status='sending' AND lease_until<=p_now;
 -- Cancel/replan only unsent unleased work. Legacy, sent and uncertain rows are immutable here.
 WITH desired AS (
  SELECT o.event_id,o.occurrence_date,
   (o.occurrence_date+o.start_time) AT TIME ZONE o.timezone AS due_at,
   jsonb_build_object('event_id',o.event_id,'occurrence_date',o.occurrence_date,'title',o.event_title,
       'start_time',o.start_time,'end_time',o.end_time,'timezone',o.timezone) AS payload
  FROM public.generate_event_occurrences(
    ((p_now-p_lookback) AT TIME ZONE 'Asia/Kolkata')::date,
    ((p_now+p_lookahead) AT TIME ZONE 'Asia/Kolkata')::date) o
 )
 INSERT INTO public.reminder_deliveries(event_id,occurrence_date,managed_by,due_at,payload,retry_at)
 SELECT event_id,occurrence_date,'m2e',due_at,payload,due_at FROM desired
 WHERE due_at BETWEEN p_now-p_lookback AND p_now+p_lookahead
 ON CONFLICT(event_id,occurrence_date) DO UPDATE SET due_at=excluded.due_at,payload=excluded.payload,
     status=CASE WHEN public.reminder_deliveries.status='cancelled' THEN 'pending' ELSE public.reminder_deliveries.status END,
     retry_at=CASE WHEN public.reminder_deliveries.payload IS DISTINCT FROM excluded.payload THEN excluded.due_at
              ELSE public.reminder_deliveries.retry_at END
 WHERE public.reminder_deliveries.managed_by='m2e'
   AND public.reminder_deliveries.status IN ('pending','failed','cancelled');
 GET DIAGNOSTICS affected=ROW_COUNT;
 UPDATE public.reminder_deliveries d SET status='cancelled',worker_token=NULL,lease_until=NULL
 WHERE d.managed_by='m2e' AND d.status IN ('pending','failed') AND
   (d.due_at<p_now-p_lookback OR NOT EXISTS (
    SELECT FROM public.generate_event_occurrences(d.occurrence_date,d.occurrence_date) o
    WHERE o.event_id=d.event_id));
 RETURN affected;
END $$;

CREATE FUNCTION public.claim_occurrence_reminders(p_now timestamptz DEFAULT now(),p_limit integer DEFAULT 20,
 p_lease interval DEFAULT interval '2 minutes')
RETURNS TABLE(delivery_id bigint,event_id bigint,occurrence_date date,payload jsonb,worker_token uuid,lease_until timestamptz)
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
 IF p_limit IS NULL OR p_limit NOT BETWEEN 1 AND 100 OR p_lease IS NULL
    OR p_lease<interval '10 seconds' OR p_lease>interval '10 minutes' THEN
    RAISE EXCEPTION 'Invalid reminder claim bounds' USING ERRCODE='22023'; END IF;
 PERFORM public.refresh_occurrence_reminders(p_now);
 RETURN QUERY WITH candidates AS (
  SELECT d.id FROM public.reminder_deliveries d WHERE d.managed_by='m2e'
   AND d.status IN ('pending','failed') AND d.attempts<5 AND d.due_at<=p_now AND d.retry_at<=p_now
  ORDER BY d.due_at,d.id FOR UPDATE SKIP LOCKED LIMIT p_limit
 ) UPDATE public.reminder_deliveries d SET status='sending',attempts=d.attempts+1,
      worker_token=gen_random_uuid(),lease_until=p_now+p_lease,claimed_at=p_now,error_message=NULL
 FROM candidates c WHERE d.id=c.id
 RETURNING d.id,d.event_id,d.occurrence_date,d.payload,d.worker_token,d.lease_until;
END $$;

CREATE FUNCTION public.finish_occurrence_reminder(p_delivery_id bigint,p_worker_token uuid,
 p_outcome text,p_now timestamptz DEFAULT now()) RETURNS boolean
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE d public.reminder_deliveries%ROWTYPE;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 IF p_outcome IS NULL OR p_outcome NOT IN ('sent','not_accepted','uncertain') OR p_now IS NULL OR NOT isfinite(p_now) THEN
    RAISE EXCEPTION 'Invalid delivery outcome' USING ERRCODE='22023'; END IF;
 SELECT * INTO d FROM public.reminder_deliveries q WHERE q.id=p_delivery_id
 AND q.managed_by='m2e' AND q.status='sending' AND q.worker_token=p_worker_token FOR UPDATE;
 IF NOT FOUND OR d.lease_until<=p_now THEN RETURN false; END IF;
 UPDATE public.reminder_deliveries SET
    status=CASE WHEN p_outcome='sent' THEN 'sent' WHEN p_outcome='uncertain' THEN 'uncertain'
                WHEN d.attempts>=5 THEN 'dead' ELSE 'failed' END,
    sent_at=CASE WHEN p_outcome='sent' THEN p_now ELSE NULL END,
    retry_at=CASE WHEN p_outcome='not_accepted' THEN p_now+make_interval(secs=>least(3600,30*power(2,d.attempts-1)::int)) ELSE NULL END,
    worker_token=NULL,lease_until=NULL,
    error_message=CASE WHEN p_outcome='uncertain' THEN 'Transport acceptance unknown; reconciliation required'
                       WHEN p_outcome='not_accepted' THEN 'Transport confirmed not accepted' ELSE NULL END
 WHERE id=d.id;
 RETURN true;
END $$;

-- Block approved schedule changes while an external send may be in flight.
-- This applies to both legacy and v2 event changes without changing either API signature.
CREATE FUNCTION public.guard_inflight_occurrence_change() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE target bigint;
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 IF TG_TABLE_NAME='schedule_events' THEN target:=OLD.id;
 ELSIF TG_OP='DELETE' THEN target:=OLD.event_id;
 ELSE target:=NEW.event_id; END IF;
 IF EXISTS(SELECT FROM public.reminder_deliveries d WHERE d.event_id=target AND d.managed_by='m2e'
    AND d.status='sending' AND d.lease_until>now()) THEN
    RAISE EXCEPTION 'Reminder send is in flight; retry schedule decision after reconciliation' USING ERRCODE='55000'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$;
CREATE TRIGGER guard_event_send BEFORE UPDATE OR DELETE ON public.schedule_events
 FOR EACH ROW EXECUTE FUNCTION public.guard_inflight_occurrence_change();
CREATE TRIGGER guard_rule_send BEFORE UPDATE OR DELETE ON public.recurrence_rules
 FOR EACH ROW EXECUTE FUNCTION public.guard_inflight_occurrence_change();
CREATE TRIGGER guard_override_send BEFORE INSERT OR UPDATE OR DELETE ON public.schedule_occurrence_overrides
 FOR EACH ROW EXECUTE FUNCTION public.guard_inflight_occurrence_change();
