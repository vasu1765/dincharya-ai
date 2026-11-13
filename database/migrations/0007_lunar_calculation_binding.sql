-- Correct a demonstrated42702 without editing the committed0006 migration.
DO $migration$
DECLARE definition text; original text; corrected text;
BEGIN
 IF current_database()<>'dincharya_app_test' OR session_user<>'synthetic_test' THEN
  RAISE EXCEPTION 'Isolated synthetic lunar setup required'; END IF;
 SELECT pg_get_functiondef(p.oid),p.prosrc INTO definition,original FROM pg_proc p
 WHERE p.oid='lunar_api.record_calculation(uuid,uuid,bigint,jsonb,text,jsonb,date)'::regprocedure
 AND p.prosecdef AND p.proowner='dincharya_lunar_executor'::regrole;
 IF NOT FOUND OR position('AS $function$'||original||'$function$' IN definition)=0
   OR position('old.command IS DISTINCT FROM command)' IN original)=0 THEN
  RAISE EXCEPTION 'Calculation source requires explicit review'; END IF;
 corrected:=E'<<lunar_calculation_body>>\n'||replace(original,
   'old.command IS DISTINCT FROM command)', 'old.command IS DISTINCT FROM lunar_calculation_body.command)');
 EXECUTE replace(definition,'AS $function$'||original||'$function$','AS '||quote_literal(corrected));
END $migration$;
