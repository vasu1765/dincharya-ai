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
  if [[ -n $id ]]; then
    [[ $(docker inspect -f '{{index .Config.Labels "org.dincharya.release"}}' "$id") == "$run" ]] && docker rm -fv "$id" >/dev/null || rc=1
  fi
  inventory > "$tmp/after" && cmp -s "$tmp/before" "$tmp/after" || rc=1
  rm -rf -- "$tmp"
  exit "$rc"
}
trap cleanup EXIT
git archive "$REV" | tar -x -C "$tmp"
docker run --rm --pull never --network none --read-only -v "$tmp:/repo:ro" -w /repo -e PYTHONPATH=/repo --entrypoint python "$app" -B -m unittest discover -s tests -p test_daily_live_release.py
export POSTGRES_PASSWORD=$(openssl rand -hex 32)
id=$(docker run --pull never --network none --tmpfs /var/lib/postgresql/data --label "org.dincharya.release=$run" -d -e POSTGRES_PASSWORD -e POSTGRES_DB=dincharya_personal_candidate "$pg")
unset POSTGRES_PASSWORD
sql() { docker exec -i "$id" psql -XqAt -v ON_ERROR_STOP=1 -U postgres -d dincharya_personal_candidate "$@"; }
for _ in {1..60}; do
  if [[ $(docker exec "$id" cat /proc/1/comm) == postgres ]] && sql -c 'select 1' >/dev/null 2>&1; then break; fi
  sleep 1
done
source tests/personal_migration_diagnostic.sh
for f in database/personal/*.sql; do run_personal_migration "$f"; done
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
 FOR i IN 1..5 LOOP PERFORM beta.live_gate(903,904,pin,'bounded','sendMessage'); END LOOP;
 PERFORM beta.live_gate(903,904,pin,'bounded','reminder');
 IF beta.live_gate(903,904,pin,'bounded','check')<>-1 THEN RAISE EXCEPTION 'missing cap'; END IF;
 BEGIN
   PERFORM beta.live_gate(903,904,pin,'bounded','sendMessage');
   RAISE EXCEPTION 'unexpected seventh attempt' USING ERRCODE='P9999';
 EXCEPTION WHEN raise_exception THEN NULL; END;
END $$;
RESET SESSION AUTHORIZATION;
DO $$ BEGIN
 IF has_function_privilege('personal_observer','beta.reconcile(uuid,bigint,text,bigint,bigint,uuid,uuid,text,boolean)','EXECUTE')
 OR NOT has_function_privilege('personal_observer','beta.health()','EXECUTE') THEN RAISE EXCEPTION 'observer privilege'; END IF;
END $$;
SQL
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
 IF beta.live_gate(903,904,repeat('b',64),'daily','check')<>81 THEN RAISE EXCEPTION 'cursor'; END IF;
END $$;
SQL
