#!/usr/bin/env bash
# Run explicitly with bash. Never enable shell tracing: subprocesses use secrets.
set +x
set -Eeuo pipefail
umask 077
exec 4>&2

capture_dir=''
stage='preflight'
finalization_log=''
fail() { printf '%s\n' "$1" >&4; on_error 1 "${BASH_LINENO[0]}"; }
on_error() {
  trap - ERR
  printf 'Capture failed: stage=%s exit=%s line=%s. No completed baseline was declared.\n' \
    "$stage" "${1:-1}" "${2:-unknown}" >&4
  if [[ -n "$capture_dir" ]]; then
    printf 'Partial artifacts and private diagnostics remain in: %s\n' "$capture_dir" >&4
    if [[ -n "$finalization_log" ]]; then
      printf 'Private finalization diagnostics: %s\n' "$finalization_log" >&4
    fi
  fi
  exit 1
}
trap 'on_error "$?" "$LINENO"' ERR
trap 'on_error 130 "$LINENO"' INT
trap 'on_error 143 "$LINENO"' TERM

for dependency in docker python3 realpath mktemp sha256sum find sort xargs date mv df dirname; do
  command -v "$dependency" >/dev/null 2>&1 || fail "Missing dependency: $dependency"
done
[[ -n "${BASELINE_BACKUP_ROOT:-}" ]] || fail 'Set BASELINE_BACKUP_ROOT to an existing private directory outside the project.'
[[ "$BASELINE_BACKUP_ROOT" = /* ]] || fail 'BASELINE_BACKUP_ROOT must be absolute.'
app_db="${BASELINE_APP_DB-dincharya_app}"
[[ "$app_db" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ && ${#app_db} -le 63 ]] || fail 'BASELINE_APP_DB must be a plain ASCII database identifier of 1-63 characters.'
script_parent="$(dirname -- "${BASH_SOURCE[0]}")" || fail 'Cannot resolve script directory.'
project_dir="$(cd -- "$script_parent/.." && pwd -P)" || fail 'Cannot resolve project directory.'
backup_root="$(realpath -e -- "$BASELINE_BACKUP_ROOT")" || fail 'Cannot resolve backup destination.'
[[ -d "$backup_root" && -w "$backup_root" ]] || fail 'Backup root must be an existing writable directory.'
case "$backup_root/" in "$project_dir/"*) fail 'Backup root must be outside the project.' ;; esac
# Check ownership and privacy without changing permissions on an existing directory.
python3 - "$backup_root" <<'PY'
import os, stat, sys
s = os.stat(sys.argv[1])
if s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) != 0o700:
    sys.exit('Backup root must be owned by this user and have permissions exactly 700.')
PY
# Check available bytes before creating even the capture directory or log.
# Decimal GB (1 GB = 1,000,000,000 bytes); positive decimals are accepted.
disk_available="$(LC_ALL=C df --block-size=1 --output=avail -- "$backup_root")" || fail 'Disk-space check failed.'
python3 - "${BASELINE_MIN_FREE_GB-5}" "$disk_available" <<'PY'
from decimal import Decimal
import re, sys
minimum, report = sys.argv[1:]
if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', minimum) or Decimal(minimum) <= 0:
    sys.exit('BASELINE_MIN_FREE_GB must be a positive decimal number of GB.')
lines = report.splitlines()
if len(lines) != 2 or not lines[1].strip().isdigit():
    sys.exit('Cannot determine available disk space from df.')
if Decimal(lines[1].strip()) < Decimal(minimum) * 1_000_000_000:
    sys.exit('Insufficient free disk space; no capture artifacts were created.')
PY
capture_timestamp="$(date -u +%Y%m%dT%H%M%SZ)" || fail 'Cannot obtain capture timestamp.'
capture_dir="$(mktemp -d "$backup_root/baseline-$capture_timestamp-XXXXXX")" || fail 'Cannot create private capture directory.'
diagnostics="$capture_dir/diagnostics.private.log"
exec 3>>"$diagnostics"
# All tool diagnostics stay private, never in the terminal.
exec 2>&3
compose=(docker compose --project-directory "$project_dir" -f "$project_dir/compose.yaml")
stage='service verification'
"${compose[@]}" version >/dev/null

for service in postgres n8n; do
  container_id="$("${compose[@]}" ps -q "$service")" || fail 'Cannot identify required container.'
  [[ -n "$container_id" && "$container_id" != *$'\n'* ]] || fail 'Expected exactly one running container per service.'
  running="$(docker inspect --format '{{.State.Running}}' "$container_id")" || fail 'Cannot inspect container state.'
  [[ "$running" = true ]] || fail 'A required service is not running.'
  if [[ "$service" = postgres ]]; then
    health="$(docker inspect --format '{{.State.Health.Status}}' "$container_id")" || fail 'Cannot inspect PostgreSQL health.'
    [[ "$health" = healthy ]] || fail 'PostgreSQL is not healthy.'
  fi
  docker inspect --format '{{.Name}} image={{.Image}} mounts={{json .Mounts}}' \
    "$container_id" >> "$capture_dir/runtime.txt"
done
"${compose[@]}" exec -T postgres postgres --version >> "$capture_dir/runtime.txt"
"${compose[@]}" exec -T postgres pg_dump --version >> "$capture_dir/runtime.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$capture_dir/started-at.txt"

# Use the live n8n database name, without outputting credentials or sourcing .env.
n8n_db="$("${compose[@]}" exec -T n8n node -e '
  const db = process.env.DB_POSTGRESDB_DATABASE;
  if (process.env.DB_TYPE !== "postgresdb" || !db ||
      process.env.DB_POSTGRESDB_HOST !== "postgres" ||
      (process.env.DB_POSTGRESDB_PORT || "5432") !== "5432") process.exit(2);
  process.stdout.write(db);
')" || fail 'Cannot determine n8n database configuration.'
[[ "$n8n_db" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ && ${#n8n_db} -le 63 ]] || fail 'n8n database must have a plain ASCII identifier.'
[[ -n "$app_db" && "$app_db" != "$n8n_db" ]] || fail 'Application and n8n databases must be distinct.'

query_database() {
  "${compose[@]}" exec -T postgres sh -c '
    export PGOPTIONS="-c default_transaction_read_only=on -c statement_timeout=60000 -c lock_timeout=10000"
    exec psql --no-password -X -qAt -v ON_ERROR_STOP=1 \
      -v expected_db="$1" -h /var/run/postgresql -p 5432 -U "$POSTGRES_USER" -d "$1"
  ' sh "$1"
}

stage='read-only application database identity validation'
# Require one schema with the complete expected application object set.
# Inspect pg_catalog only; never call scheduling functions.
identity_valid="$(query_database "$app_db" <<'SQL'
WITH required_tables(name) AS (
  VALUES ('schedule_events'), ('recurrence_rules'),
         ('schedule_change_requests'), ('reminder_deliveries')
), required_functions(name) AS (
  VALUES ('generate_event_occurrences'), ('find_schedule_conflicts'),
         ('find_occurrence_conflicts'), ('find_proposed_recurrence_conflicts'),
         ('validate_recurrence_rule'), ('validate_schedule_proposal'),
         ('process_schedule_decision'), ('approve_advanced_schedule_add'),
         ('dispatch_schedule_decision')
), candidates AS (
  SELECT n.oid FROM pg_catalog.pg_namespace n
  WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
    AND n.nspname NOT LIKE 'pg_toast%' AND n.nspname NOT LIKE 'pg_temp_%'
    AND NOT EXISTS (
      SELECT FROM required_tables r WHERE NOT EXISTS (
        SELECT FROM pg_catalog.pg_class c
        WHERE c.relnamespace = n.oid AND c.relname = r.name AND c.relkind IN ('r', 'p')
      )
    )
    AND NOT EXISTS (
      SELECT FROM required_functions r WHERE NOT EXISTS (
        SELECT FROM pg_catalog.pg_proc p
        WHERE p.pronamespace = n.oid AND p.proname = r.name AND p.prokind = 'f'
      )
    )
)
SELECT current_database() = :'expected_db' AND (SELECT count(*) FROM candidates) = 1;
SQL
)" || fail 'Application identity catalog query failed; no dumps created.'
[[ "$identity_valid" = t ]] || fail 'Expected application tables/functions are missing or ambiguous; no dumps created.'
printf 'Expected application tables and all nine function names found in one schema; signatures not verified.\n' \
  > "$capture_dir/database-identity.txt"

# Every PostgreSQL connection is forced read-only. No application functions run.
dump_database() {
  local database="$1" destination="$2"
  "${compose[@]}" exec -T postgres sh -c '
    export PGOPTIONS="-c default_transaction_read_only=on -c statement_timeout=0"
    exec pg_dump --no-password -h /var/run/postgresql -p 5432 -U "$POSTGRES_USER" -d "$1" \
      --format=custom --create --lock-wait-timeout=10s
  ' sh "$database" > "$destination.partial"
  [[ -s "$destination.partial" ]]
  "${compose[@]}" exec -T postgres pg_restore --list \
    < "$destination.partial" > "$destination.contents.partial"
  [[ -s "$destination.contents.partial" ]]
  mv -- "$destination.partial" "$destination"
  mv -- "$destination.contents.partial" "$destination.contents"
}
stage='application database dump and archive validation'
dump_database "$app_db" "$capture_dir/application.dump"
stage='n8n database dump and archive validation'
dump_database "$n8n_db" "$capture_dir/n8n.dump"

stage='application schema capture'
"${compose[@]}" exec -T postgres sh -c '
  export PGOPTIONS="-c default_transaction_read_only=on"
  exec pg_dump --no-password -h /var/run/postgresql -p 5432 -U "$POSTGRES_USER" -d "$1" \
    --schema-only --no-owner --no-privileges --lock-wait-timeout=10s
' sh "$app_db" > "$capture_dir/application-schema.sql.partial"
[[ -s "$capture_dir/application-schema.sql.partial" ]]
mv -- "$capture_dir/application-schema.sql.partial" "$capture_dir/application-schema.sql"

query_n8n() {
  query_database "$n8n_db"
}
# Discover standard n8n workflow storage without assuming the database search_path.
stage='read-only PostgreSQL workflow snapshot'
workflow_tables="$(query_n8n <<'SQL'
SELECT count(*) FROM information_schema.tables
WHERE table_name = 'workflow_entity' AND table_type = 'BASE TABLE'
  AND table_schema NOT IN ('pg_catalog', 'information_schema');
SQL
)" || fail 'Cannot discover workflow snapshot storage.'
workflow_status='unsupported'
if [[ "$workflow_tables" = 1 ]]; then
  query_n8n > "$capture_dir/workflows-current.raw.json.partial" <<'SQL'
SELECT format(
  'SELECT COALESCE(jsonb_agg(to_jsonb(w) ORDER BY w.id), ''[]''::jsonb) FROM %I.%I w;',
  table_schema, table_name)
FROM information_schema.tables
WHERE table_name = 'workflow_entity' AND table_type = 'BASE TABLE'
  AND table_schema NOT IN ('pg_catalog', 'information_schema')
\gexec
SQL
  python3 - "$capture_dir/workflows-current.raw.json.partial" \
    "$capture_dir/workflow-snapshot-summary.json" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    workflows = json.load(f)
required = {'Dincharya - Telegram Chat', 'Dincharya - Scheduled Reminders'}
if not isinstance(workflows, list):
    sys.exit('Workflow snapshot is not an array.')
if any(not isinstance(w, dict) or not all(k in w for k in ('id', 'name', 'nodes', 'connections'))
       or not isinstance(w['name'], str)
       or not isinstance(w['id'], (str, int)) or isinstance(w['id'], bool)
       or not isinstance(w['nodes'], list) or not isinstance(w['connections'], dict)
       or any(not isinstance(node, dict) for node in w['nodes'])
       for w in workflows):
    sys.exit('Unsupported workflow structure.')
names = {w['name'] for w in workflows}
summary = {
    'artifact_type': 'read-only PostgreSQL snapshot',
    'guaranteed_n8n_importable': False,
    'total_workflow_count': len(workflows),
    'expected_workflows_present': {name: name in names for name in sorted(required)},
}
with open(sys.argv[2], 'w') as f:
    json.dump(summary, f, indent=2)
    f.write('\n')
if not required.issubset(names):
    sys.exit('An expected workflow is missing.')
PY
  mv -- "$capture_dir/workflows-current.raw.json.partial" "$capture_dir/workflows-current.raw.json"
  workflow_status='completed'
  printf '%s\n' \
    'workflows-current.raw.json is a read-only PostgreSQL snapshot, NOT a guaranteed n8n-importable workflow export.' \
    'Current rows only; published/history versions remain in n8n.dump.' \
    'Counts and expected-name presence are recorded in workflow-snapshot-summary.json.' \
    > "$capture_dir/workflow-export-status.txt"
elif [[ "$workflow_tables" = 0 ]]; then
  printf 'UNSUPPORTED: standard workflow_entity table absent. Full n8n database preserved; manual version-aware export required.\n' > "$capture_dir/workflow-export-status.txt"
else
  fail 'Ambiguous workflow storage; refusing to select a schema.'
fi

printf '%s\n' \
  'database_capture=completed' \
  "workflow_snapshot=$workflow_status" \
  'full_recovery_backup=not_completed' \
  'restore_test=not_performed' \
  'backup_encryption=none_applied_by_script' \
  > "$capture_dir/capture-status.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$capture_dir/finished-at.txt"
stage='artifact finalization'
# Refuse to seal any incomplete payload. No artifact changes after this check,
# except closing diagnostics and creating the checksum manifest/completion marker.
python3 - "$capture_dir" <<'PY'
from pathlib import Path
import os, stat, sys
root = Path(sys.argv[1])
paths = [root, *root.rglob('*')]
if any(p.name.endswith('.partial') for p in paths):
    sys.exit('Unfinalized artifacts remain; refusing to generate checksums.')
for p in paths:
    s = p.lstat()
    expected = 0o700 if stat.S_ISDIR(s.st_mode) else 0o600
    if (not (stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode))
            or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) != expected):
        sys.exit('Artifact ownership or permissions do not meet private backup requirements.')
PY
# Keep late-stage errors in a private sibling log, outside the sealed payload.
# It is deliberately not part of SHA256SUMS, since hashing can append errors.
finalization_log="$(mktemp --suffix=.private.log "$capture_dir.finalization-XXXXXX")" || fail 'Cannot create finalization diagnostics.'
exec 2>>"$finalization_log"
exec 3>&-
stage='checksum generation and verification'
(
  cd -- "$capture_dir"
  find . -type f ! -name SHA256SUMS ! -name SHA256SUMS.partial ! -name COMPLETE -print0 \
    | LC_ALL=C sort -z | xargs -0 sha256sum > SHA256SUMS.partial
  mv -- SHA256SUMS.partial SHA256SUMS
  sha256sum --check SHA256SUMS > /dev/null
)
stage='completion marker'
printf '%s\n' \
  'CAPTURE_COMPLETE: database capture and SHA-256 verification succeeded.' \
  "database_capture=completed workflow_snapshot=$workflow_status full_recovery_backup=not_completed" \
  'SHA256SUMS excludes itself and this COMPLETE marker.' \
  'Not a complete disaster-recovery backup; restore not tested. Review workflow-export-status.txt.' \
  > "$capture_dir/COMPLETE.partial"
mv -- "$capture_dir/COMPLETE.partial" "$capture_dir/COMPLETE"
printf 'Baseline captured in: %s\n' "$capture_dir"
printf 'Database capture completed; workflow snapshot: %s; full recovery backup NOT completed.\n' "$workflow_status"
printf 'Private finalization diagnostics: %s\n' "$finalization_log"
printf 'Read workflow-export-status.txt privately. Encryption keys and environment files were NOT captured.\n'
printf 'Backups are unencrypted by this script; Unix permissions do not protect against Windows administrators or physical disk access.\n'
