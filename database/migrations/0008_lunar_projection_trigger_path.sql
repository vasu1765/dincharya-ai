-- Baseline trigger uses unqualified recurrence_rules. Preserve body/privileges;
-- give that invoker helper a fixed path, with temp relations explicitly last.
DO $$ BEGIN
 IF current_database()<>'dincharya_app_test' OR session_user<>'synthetic_test' OR
    NOT EXISTS(SELECT FROM pg_proc WHERE oid='public.sync_legacy_recurrence_rule()'::regprocedure
      AND NOT prosecdef) THEN RAISE EXCEPTION 'Reviewed synthetic trigger required'; END IF;
 IF EXISTS(SELECT FROM pg_roles r WHERE r.rolcanlogin AND NOT r.rolsuper
   AND has_schema_privilege(r.oid,'public','CREATE')) THEN
  RAISE EXCEPTION 'Untrusted public schema writer'; END IF;
END $$;
ALTER FUNCTION public.sync_legacy_recurrence_rule() SET search_path=pg_catalog,public,pg_temp;
