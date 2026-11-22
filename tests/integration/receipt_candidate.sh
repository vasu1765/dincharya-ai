#!/usr/bin/env bash
# Disposable SQL-only candidate check. Requires an approved local PG17 image ID.
set -euo pipefail
: "${REV:?candidate SHA}" "${PG:?full local PostgreSQL 17 image ID}"
test "$(git rev-parse HEAD)" = "$REV"
test -z "$(git status --porcelain)"
test "$(docker info --format '{{.ID}}')" = 44c1ef83-c50e-4ecc-8f19-4b112bc40f29
test "$(docker image inspect --format '{{.Id}}' "$PG")" = "$PG"
[[ $PG =~ ^sha256:[0-9a-f]{64}$ ]]
cid=$(docker run --pull never --network none -d --tmpfs /var/lib/postgresql/data:rw \
  -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_USER=synthetic_test \
  -e POSTGRES_DB=dincharya_app_test "$PG" postgres -c listen_addresses=)
trap 'docker rm -fv "$cid" >/dev/null' EXIT
psql=(docker exec -i "$cid" psql -XAtq -v ON_ERROR_STOP=1 -U synthetic_test -d dincharya_app_test)
for _ in {1..60}; do
  if [[ $(docker exec "$cid" cat /proc/1/comm) == postgres ]] && "${psql[@]}" -c 'SELECT 1' >/dev/null 2>&1; then break; fi
  sleep 1
done
[[ $("${psql[@]}" -c 'SHOW server_version_num') == 17???? ]]
cat tests/integration/m2h_development_schema.sql | "${psql[@]}"
python3 -B - <<'PY' | "${psql[@]}" >/dev/null
from pathlib import Path
from database.migrate import render_migrations
print(render_migrations(sorted(Path('database/migrations').glob('*.sql'))))
PY
"${psql[@]}" <<'SQL'
INSERT INTO public.schedule_events(title,event_date,start_time) VALUES ('Receipt fixture',current_date,'12:00');
INSERT INTO lunar_private.notification_slot(event_id,occurrence_date,offset_minutes,due_at,payload,status,attempts,worker_token,lease_until)
 SELECT id,current_date,0,now(),'{}','sending',1,'00000000-0000-0000-0000-000000000001',now()+interval '2 minutes' FROM public.schedule_events;
INSERT INTO public.reminder_deliveries(event_id,occurrence_date,managed_by,status,attempts,worker_token,lease_until)
 SELECT id,current_date,'m2e','sending',1,'00000000-0000-0000-0000-000000000001',now()+interval '2 minutes' FROM public.schedule_events;
SET ROLE dincharya_reminder_worker;
DO $$
DECLARE ns text; tok uuid:='00000000-0000-0000-0000-000000000001'; ok boolean;
BEGIN
 IF has_table_privilege(current_user,'public.reminder_deliveries','UPDATE')
 OR has_table_privilege(current_user,(SELECT c.oid FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
     WHERE n.nspname='lunar_private' AND c.relname='notification_slot'),'UPDATE') THEN RAISE EXCEPTION 'unexpected table grant'; END IF;
 FOREACH ns IN ARRAY ARRAY['notification_worker_api','reminder_worker_api'] LOOP
  BEGIN
   EXECUTE format('SELECT %I.finish_occurrence_reminder(1,$1,''sent'',now())',ns) USING tok;
   RAISE EXCEPTION 'missing receipt accepted';
  EXCEPTION WHEN check_violation OR invalid_parameter_value THEN NULL;
  END;
  BEGIN
   EXECUTE format('SELECT %I.acknowledge_occurrence_reminder(1,$1,''sent'',now(),NULL,NULL)',ns) USING tok;
   RAISE EXCEPTION 'absent pair accepted';
  EXCEPTION WHEN check_violation OR invalid_parameter_value THEN NULL;
  END;
  EXECUTE format('SELECT %I.acknowledge_occurrence_reminder(1,$1,''sent'',now(),101,42)',ns) INTO ok USING tok;
  IF ok IS DISTINCT FROM true THEN RAISE EXCEPTION 'valid receipt failed'; END IF;
  EXECUTE format('SELECT %I.acknowledge_occurrence_reminder(1,$1,''sent'',now(),101,42)',ns) INTO ok USING tok;
  IF ok IS DISTINCT FROM false THEN RAISE EXCEPTION 'lease replay'; END IF;
 END LOOP;
END $$;
RESET ROLE;
DO $$ BEGIN
 IF (SELECT count(*) FROM lunar_private.notification_slot WHERE status='sent' AND telegram_chat_id=101 AND telegram_message_id=42)<>1
 OR (SELECT count(*) FROM public.reminder_deliveries WHERE status='sent' AND telegram_chat_id=101 AND telegram_message_id=42)<>1 THEN
 RAISE EXCEPTION 'receipt storage mismatch'; END IF;
END $$;
SQL
echo 'PASS fresh PG17 managed and slot API negative, valid pair, scoped grants and lease replay'
