#!/usr/bin/env bash
set -euo pipefail
: "${REV:?exact review revision}"
[[ $(git rev-parse HEAD) == "$REV" && -z $(git status --porcelain) ]]
pg=sha256:ff87138949ad9a46f32ff23bd6852b52ce024a13dffe9b4087be98292cdd3b4f
[[ $(docker image inspect --format '{{.Id}}' "$pg") == "$pg" ]]
# No ports, host mounts, client path or connection to an existing database.
run=$(openssl rand -hex 16)
label="org.dincharya.daily-sql=$run"
export POSTGRES_PASSWORD
POSTGRES_PASSWORD=$(openssl rand -hex 32)
id=$(docker run --pull never --label "$label" --network none --tmpfs /var/lib/postgresql/data -d -e POSTGRES_PASSWORD -e POSTGRES_DB=dincharya_beta_rehearsal "$pg")
unset POSTGRES_PASSWORD
cleanup() {
  [[ $(docker inspect --format '{{index .Config.Labels "org.dincharya.daily-sql"}}' "$id") == "$run" ]] && docker rm -fv "$id" >/dev/null
}
trap cleanup EXIT
sql() { docker exec -i "$id" psql -XqAt -v ON_ERROR_STOP=1 -U postgres -d dincharya_beta_rehearsal "$@"; }
for _ in {1..60}; do
  if [[ $(docker exec "$id" cat /proc/1/comm) == postgres ]] && sql -c 'select 1' >/dev/null 2>&1; then break; fi
  sleep 1
done
sql -f - < database/personal_beta/0001_civil.sql
sql -f - < database/daily_review/0001_preview.sql
sql -c 'INSERT INTO beta.ui_bot VALUES(true,902)'
sql <<'SQL'
SET SESSION AUTHORIZATION daily_gateway;
DO $$
DECLARE p uuid; t uuid; r record;
BEGIN
 SELECT proposal,ticket INTO STRICT p,t FROM beta.ui_draft(101,902,17,'Practice','once',current_date+2,'07:00','{60,0}');
 IF NOT beta.ui_finish(101,902,t,true,17) THEN RAISE EXCEPTION 'preview receipt'; END IF;
 IF EXISTS(SELECT FROM beta.ui_decide(101,902,p,18,true)) THEN RAISE EXCEPTION 'foreign origin'; END IF;
END $$;
SQL
token=$(sql -c 'select id from beta.proposal')
decide="SET SESSION AUTHORIZATION daily_gateway; SELECT status FROM beta.ui_decide(101,902,'$token',17,true)"
sql -c "$decide" >/dev/null &
first=$!
sql -c "$decide" >/dev/null
wait "$first"
[[ $(sql -c "SELECT count(*) FROM beta.occurrence") == 1 ]]
[[ $(sql -c "SELECT count(*) FROM beta.slot") == 2 ]]
[[ $(sql -c "SELECT count(*) FROM beta.ui_call WHERE method='editMessageText'") == 1 ]]
[[ $(sql -c "SELECT count(*) FROM beta.ui_call WHERE method='answerCallbackQuery'") == 1 ]]
sql -c "SET SESSION AUTHORIZATION daily_gateway; SELECT status FROM beta.ui_decide(101,902,'$token',17,false)" >/dev/null
[[ $(sql -c 'SELECT state FROM beta.proposal') == active ]]
echo 'PASS scoped decision concurrency, conflict with subsequent Cancel, one appointment and two slots'
