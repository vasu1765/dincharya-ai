-- Unknown historical receipts stay NULL; never infer IDs from existing history.
ALTER TABLE public.reminder_deliveries
 ADD COLUMN telegram_chat_id bigint,
 ADD COLUMN telegram_message_id bigint,
 ADD CONSTRAINT reminder_telegram_receipt_pair
  CHECK ((telegram_chat_id IS NULL)=(telegram_message_id IS NULL)),
 ADD CONSTRAINT reminder_telegram_receipt_valid
  CHECK (telegram_chat_id IS NULL OR (telegram_chat_id<>0 AND telegram_message_id>0
    AND status='sent' AND managed_by IS NOT DISTINCT FROM 'm2e'));
CREATE UNIQUE INDEX reminder_telegram_receipt_identity
 ON public.reminder_deliveries(telegram_chat_id,telegram_message_id)
 WHERE telegram_chat_id IS NOT NULL;

-- Keep the original four-argument acknowledgement API intact for old workers.
-- Its lease/token check and both writes execute within this one SQL transaction.
CREATE FUNCTION public.acknowledge_occurrence_reminder(p_delivery_id bigint,p_worker_token uuid,
 p_outcome text,p_now timestamptz,p_telegram_chat_id bigint DEFAULT NULL,
 p_telegram_message_id bigint DEFAULT NULL) RETURNS boolean
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
 IF (p_telegram_chat_id IS NULL)<>(p_telegram_message_id IS NULL)
    OR (p_telegram_chat_id IS NOT NULL AND
      (p_telegram_chat_id=0 OR p_telegram_message_id<=0 OR p_outcome IS DISTINCT FROM 'sent')) THEN
  RAISE EXCEPTION 'Invalid delivery receipt' USING ERRCODE='22023';
 END IF;
 PERFORM pg_advisory_xact_lock(20261112,1);
 IF NOT public.finish_occurrence_reminder(p_delivery_id,p_worker_token,p_outcome,p_now) THEN
  RETURN false;
 END IF;
 IF p_telegram_chat_id IS NOT NULL THEN
  UPDATE public.reminder_deliveries SET telegram_chat_id=p_telegram_chat_id,
   telegram_message_id=p_telegram_message_id WHERE id=p_delivery_id;
 END IF;
 RETURN true;
END $$;
