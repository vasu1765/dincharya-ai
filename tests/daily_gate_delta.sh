#!/usr/bin/env bash
set -euo pipefail
[[ $(git rev-parse HEAD) == "${REV:?exact revision}" && -z $(git status --porcelain) ]]
sha256sum -c docs/daily-release.sha256
pg=sha256:ff87138949ad9a46f32ff23bd6852b52ce024a13dffe9b4087be98292cdd3b4f
app=sha256:fff0b1b58321339ad0de04804548cb8ff14c9a929e6eead08ce3cd96535493ca
tmp=$(mktemp -d)
run=$(openssl rand -hex 16)
id=
inventory() { docker ps -aq --no-trunc | sort; docker network ls -q --no-trunc | sort; docker volume ls -q | sort; docker image ls -q --no-trunc | sort; }
inventory > "$tmp/before"
cleanup() {
  rc=$?
  cleanup_rc=0
  if [[ -n $id ]]; then
    [[ $(docker inspect -f '{{index .Config.Labels "org.dincharya.release"}}' "$id") == "$run" ]] && docker rm -fv "$id" >/dev/null || cleanup_rc=1
  fi
  inventory > "$tmp/after" && cmp -s "$tmp/before" "$tmp/after" || cleanup_rc=1
  rm -rf -- "$tmp" || cleanup_rc=1
  if (( cleanup_rc )); then
    echo "FAIL cleanup or inventory" >&2
  else
    echo "PASS disposable cleanup and unchanged Docker inventory"
  fi
  exit "$(( rc != 0 ? rc : cleanup_rc ))"
}
trap cleanup EXIT
stage() { printf "STAGE %s\n" "$1"; }
stage offline_http_mock
git archive "$REV" | tar -x -C "$tmp"
docker run --rm --pull never --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777 -v "$tmp:/repo:ro" -w /repo -e PYTHONPATH=/repo --entrypoint python "$app" -B -m unittest discover -s tests -p test_daily_live_release.py
stage postgres_bootstrap
export POSTGRES_PASSWORD=$(openssl rand -hex 32)
id=$(docker run --pull never --network none --tmpfs /var/lib/postgresql/data --label "org.dincharya.release=$run" -d -e POSTGRES_PASSWORD -e POSTGRES_DB=dincharya_personal_candidate "$pg")
unset POSTGRES_PASSWORD
sql() { docker exec -i "$id" psql -XqAt -v ON_ERROR_STOP=1 -U postgres -d dincharya_personal_candidate "$@"; }
ready=false
for _ in {1..60}; do
  if [[ $(docker exec "$id" cat /proc/1/comm) == postgres ]] && sql -c 'select 1' >/dev/null 2>&1; then ready=true; break; fi
  sleep 1
done
[[ $ready == true ]] || { echo "FAIL postgres_readiness" >&2; exit 1; }
source tests/personal_migration_diagnostic.sh
for f in database/personal/*.sql; do run_personal_migration "$f"; done
stage bounded_budget_and_permissions
sql <<'SQL'
INSERT INTO beta.authority(singleton,recipient,bot,enabled,lookback) VALUES(true,903,904,true,interval '5 minutes');
INSERT INTO beta.live_release(epoch,digest,profile,opens,closes)
SELECT epoch,repeat('a',64),'bounded',now()-interval '1 minute',now()+interval '10 minutes' FROM beta.authority;
SET SESSION AUTHORIZATION personal_gateway;
SELECT beta.acquire();
DO $$
DECLARE pin text:=repeat('a',64);
BEGIN
 PERFORM beta.live_gate(903,904,pin,'bounded','start');
 PERFORM beta.live_gate(903,904,pin,'bounded','reminder');
 BEGIN
   PERFORM beta.live_gate(903,904,pin,'bounded','reminder');
   RAISE EXCEPTION 'unexpected second reminder' USING ERRCODE='P9999';
 EXCEPTION WHEN raise_exception THEN
   IF SQLERRM <> 'budget exhausted' THEN RAISE; END IF;
 END;
 FOR i IN 1..5 LOOP PERFORM beta.live_gate(903,904,pin,'bounded','sendMessage'); END LOOP;
 IF beta.live_gate(903,904,pin,'bounded','check')<>-1 THEN RAISE EXCEPTION 'missing cap'; END IF;
 BEGIN
   PERFORM beta.live_gate(903,904,pin,'bounded','sendMessage');
   RAISE EXCEPTION 'unexpected seventh attempt' USING ERRCODE='P9999';
 EXCEPTION WHEN raise_exception THEN
   IF SQLERRM <> 'budget exhausted' THEN RAISE; END IF;
 END;
END $$;
RESET SESSION AUTHORIZATION;
DO $$ BEGIN
 IF (SELECT (attempts,reminders) IS DISTINCT FROM (6,1) FROM beta.live_release WHERE profile='bounded')
 THEN RAISE EXCEPTION 'bounded counts'; END IF;
 IF NOT has_function_privilege('personal_gateway','beta.live_gate(bigint,bigint,text,text,text,bigint)','EXECUTE')
 OR has_function_privilege('personal_worker','beta.live_gate(bigint,bigint,text,text,text,bigint)','EXECUTE')
 OR NOT has_function_privilege('personal_worker','beta.recording_claim()','EXECUTE')
 OR has_function_privilege('personal_worker','beta.claim()','EXECUTE')
 OR has_function_privilege('personal_worker','beta.claim_notice()','EXECUTE')
 OR has_table_privilege('personal_gateway','beta.live_release','SELECT,INSERT,UPDATE,DELETE,TRUNCATE')
 OR has_table_privilege('personal_worker','beta.live_release','SELECT,INSERT,UPDATE,DELETE,TRUNCATE')
 THEN RAISE EXCEPTION 'runtime role boundaries'; END IF;
 IF has_function_privilege('personal_observer','beta.reconcile(uuid,bigint,text,bigint,bigint,uuid,uuid,text,boolean)','EXECUTE')
 OR NOT has_function_privilege('personal_observer','beta.health()','EXECUTE')
 OR has_table_privilege('personal_observer','beta.authority','SELECT')
 OR has_function_privilege('personal_observer','beta.live_gate(bigint,bigint,text,text,text,bigint)','EXECUTE')
 THEN RAISE EXCEPTION 'observer privilege'; END IF;
 IF NOT has_table_privilege('personal_backup','beta.authority','SELECT')
 OR has_table_privilege('personal_backup','beta.authority','INSERT,UPDATE,DELETE,TRUNCATE')
 OR has_function_privilege('personal_backup','beta.reconcile(uuid,bigint,text,bigint,bigint,uuid,uuid,text,boolean)','EXECUTE')
 OR has_function_privilege('personal_backup','beta.live_gate(bigint,bigint,text,text,text,bigint)','EXECUTE')
 THEN RAISE EXCEPTION 'backup privilege'; END IF;
END $$;
SQL
echo "PASS bounded six attempts, one reminder and isolated runtime roles"
stage ordinary_daily_and_cursor
# A fresh fixture epoch models the distinct, independently provisioned daily release.
sql <<'SQL'
UPDATE beta.authority SET epoch=gen_random_uuid();
INSERT INTO beta.live_release(epoch,digest,profile,opens,closes)
SELECT epoch,repeat('b',64),'daily',now()-interval '1 minute',now()+interval '1 day' FROM beta.authority;
SET SESSION AUTHORIZATION personal_gateway;
SELECT beta.acquire();
DO $$ BEGIN
 PERFORM beta.live_gate(903,904,repeat('b',64),'daily','start');
 FOR i IN 1..7 LOOP PERFORM beta.live_gate(903,904,repeat('b',64),'daily','sendMessage'); END LOOP;
 PERFORM beta.live_gate(903,904,repeat('b',64),'daily','ack',81);
END $$;
SQL
sql <<'SQL'
SET SESSION AUTHORIZATION personal_gateway;
SELECT beta.acquire();
DO $$ BEGIN
 IF NOT beta.acquire() OR beta.live_gate(903,904,repeat('b',64),'daily','check')<>81
 THEN RAISE EXCEPTION 'cursor after reconnect'; END IF;
END $$;
RESET SESSION AUTHORIZATION;
DO $$ BEGIN
 IF (SELECT (attempts,reminders,cursor_id) IS DISTINCT FROM (0,0,81::bigint)
     FROM beta.live_release WHERE profile='daily') THEN RAISE EXCEPTION 'ordinary daily ledger'; END IF;
END $$;
SQL
echo "PASS ordinary daily sends beyond six and cursor survives reconnect"
