-- Keep legacy implementations verbatim inside guarded nested blocks. No public
-- bypass alias, SECURITY DEFINER, ACL change or backup/source rewrite is needed.
DO $migration$
DECLARE signature text; original text; definition text; wrapped text; guard text;
BEGIN
 FOREACH signature IN ARRAY ARRAY[
  'public.process_schedule_decision(bigint,bigint,text,boolean)',
  'public.create_schedule_change_proposal(text,bigint,bigint,text,time without time zone,time without time zone)'
 ] LOOP
  SELECT p.prosrc,pg_get_functiondef(p.oid) INTO original,definition
   FROM pg_proc p JOIN pg_language l ON l.oid=p.prolang
   WHERE p.oid=signature::regprocedure AND l.lanname='plpgsql' AND NOT p.prosecdef;
  IF NOT FOUND OR position('AS $function$'||original||'$function$' IN definition)=0 THEN
   RAISE EXCEPTION 'Unsupported legacy function definition; explicit review required';
  END IF;
  IF signature LIKE 'public.process_schedule_decision(%' THEN
   guard := $guard$
    PERFORM pg_advisory_xact_lock(20261112,1);
    SELECT * INTO m2d_request FROM public.schedule_change_requests q
     WHERE q.id=p_request_id AND q.requested_by=p_user_id FOR UPDATE;
    -- Version tags cannot authorize the legacy entry point to mutate managed
    -- state. Only canonical rejection/discard is allowed here for these rows.
    IF FOUND AND m2d_request.status='pending' AND p_decision IS DISTINCT FROM 'reject'
       AND m2d_request.action IN ('update','remove')
       AND EXISTS(SELECT FROM public.recurrence_rules r WHERE r.event_id=m2d_request.event_id
         AND r.rule_options->>'managed_by'='m2d') THEN
     RETURN QUERY SELECT false,'Managed series requires a fresh v2 proposal'::text;
     RETURN;
    END IF;
   $guard$;
  ELSE
   guard := $guard$
    PERFORM pg_advisory_xact_lock(20261112,1);
    IF lower(btrim(p_action)) IN ('update','remove') AND EXISTS(
      SELECT FROM public.recurrence_rules r WHERE r.event_id=p_event_id
       AND r.rule_options->>'managed_by'='m2d') THEN
     RAISE EXCEPTION 'Managed series requires a fresh v2 proposal' USING ERRCODE='22023';
    END IF;
   $guard$;
  END IF;
  wrapped := E'DECLARE m2d_request public.schedule_change_requests%ROWTYPE;\nBEGIN\n'
   ||guard||E'\n<<preserved_legacy>>\n'||original
   ||CASE WHEN right(rtrim(original,E' \t\r\n'),1)=';' THEN '' ELSE ';' END||E'\nEND;\n';
  EXECUTE replace(definition,'AS $function$'||original||'$function$', 'AS '||quote_literal(wrapped));
 END LOOP;
END $migration$;

-- Direct legacy envelope submission must not create a new pending mutation of
-- a currently managed series. Existing pending requests are checked at decision
-- time above, including requests submitted before their event became managed.
CREATE FUNCTION public.guard_legacy_managed_request() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(20261112,1);
 IF NEW.action IN ('update','remove') AND NEW.proposed_data->>'api_version' IS DISTINCT FROM '2'
    AND EXISTS(SELECT FROM public.recurrence_rules r WHERE r.event_id=NEW.event_id
      AND r.rule_options->>'managed_by'='m2d') THEN
  RAISE EXCEPTION 'Managed series requires a fresh v2 proposal' USING ERRCODE='22023';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER guard_legacy_managed_request BEFORE INSERT OR UPDATE OF action,event_id,proposed_data
 ON public.schedule_change_requests FOR EACH ROW EXECUTE FUNCTION public.guard_legacy_managed_request();
