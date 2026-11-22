-- Existing sent rows may predate receipt capture. Never infer a receipt.
DO $$ BEGIN
 IF current_database()<>'dincharya_app_test' OR session_user<>'synthetic_test' THEN
  RAISE EXCEPTION 'Isolated synthetic setup required';
 END IF;
END $$;

ALTER TABLE lunar_private.notification_slot
 ADD CONSTRAINT sent_slot_requires_receipt
 CHECK (status<>'sent' OR (telegram_chat_id IS NOT NULL AND telegram_message_id IS NOT NULL))
 NOT VALID;

-- The old public functions remain available to separately scoped legacy callers.
-- Restricted worker logins have no ledger write grant. Both managed entry points
-- reject unsupported success. Preserve lease, rejection and quarantine logic.
CREATE OR REPLACE FUNCTION reminder_worker_api.acknowledge_occurrence_reminder(
 p_id bigint,p_token uuid,p_outcome text,p_now timestamptz,p_chat bigint DEFAULT NULL,p_message bigint DEFAULT NULL
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF p_outcome='sent' AND (p_chat IS NULL OR p_message IS NULL) THEN
  RAISE EXCEPTION 'Paired receipt required' USING ERRCODE='22023';
 END IF;
 RETURN public.acknowledge_occurrence_reminder(p_id,p_token,p_outcome,p_now,p_chat,p_message);
END $$;

CREATE OR REPLACE FUNCTION reminder_worker_api.finish_occurrence_reminder(
 p_id bigint,p_token uuid,p_outcome text,p_now timestamptz DEFAULT now()
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF p_outcome='sent' THEN
  RAISE EXCEPTION 'Paired receipt required' USING ERRCODE='22023';
 END IF;
 RETURN public.finish_occurrence_reminder(p_id,p_token,p_outcome,p_now);
END $$;
