-- Catalog inventory only. Never invokes application functions.
SELECT n.nspname AS schema_name, c.relname AS table_name
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'p')
  AND c.relname IN ('schedule_events', 'recurrence_rules',
                   'schedule_change_requests', 'reminder_deliveries')
ORDER BY 1, 2;

SELECT n.nspname AS schema_name, p.proname AS function_name,
       pg_catalog.pg_get_function_identity_arguments(p.oid) AS arguments,
       p.prosecdef AS security_definer
FROM pg_catalog.pg_proc p
JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
WHERE p.prokind = 'f' AND p.proname IN (
  'generate_event_occurrences', 'find_schedule_conflicts',
  'find_occurrence_conflicts', 'find_proposed_recurrence_conflicts',
  'validate_recurrence_rule', 'validate_schedule_proposal',
  'process_schedule_decision', 'approve_advanced_schedule_add',
  'dispatch_schedule_decision')
ORDER BY 1, 2, 3;
