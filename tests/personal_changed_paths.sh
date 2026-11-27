#!/usr/bin/env bash
set -euo pipefail
[[ $(git rev-parse HEAD) == "${REV:?exact candidate SHA}" && -z $(git status --porcelain) ]]
sha256sum -c docs/personal-candidate.sha256
python scripts/verify-personal-register.py
export PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1
pg=sha256:ff87138949ad9a46f32ff23bd6852b52ce024a13dffe9b4087be98292cdd3b4f
run=$(openssl rand -hex 16)
tmp=$(mktemp -d)
ids=()
inventory() { docker ps -aq --no-trunc | sort; docker volume ls -q | sort; docker network ls -q --no-trunc | sort; }
inventory > "$tmp/before"
cleanup() {
  rc=$?
  for id in "${ids[@]}"; do
    [[ $(docker inspect -f '{{index .Config.Labels "org.dincharya.personal-fixture"}}' "$id") == "$run" ]] && docker rm -fv "$id" >/dev/null || rc=1
  done
  inventory > "$tmp/after" && cmp -s "$tmp/before" "$tmp/after" || rc=1
  rm -rf -- "$tmp"
  exit "$rc"
}
trap cleanup EXIT
sql() { docker exec -i "$id" psql -XqAt -v ON_ERROR_STOP=1 -U postgres -d dincharya_personal_candidate "$@"; }
fresh() {
  local POSTGRES_PASSWORD
  POSTGRES_PASSWORD=$(openssl rand -hex 32)
  export POSTGRES_PASSWORD
  id=$(docker run --pull never --network none --label "org.dincharya.personal-fixture=$run" --tmpfs /var/lib/postgresql/data -e POSTGRES_PASSWORD -e POSTGRES_DB=dincharya_personal_candidate -d "$pg")
  ids+=("$id")
  for _ in {1..60}; do
    if [[ $(docker exec "$id" cat /proc/1/comm) == postgres ]] && sql -c 'select 1' >/dev/null 2>&1; then return; fi
    sleep 1
  done
  return 1
}
fresh
for file in database/personal/*.sql; do sql -f - < "$file"; done
sql <<'SQL'
INSERT INTO beta.authority(singleton,recipient,bot,enabled,lookback) VALUES(true,903,904,true,interval '5 minutes');
SET SESSION AUTHORIZATION personal_gateway;
SELECT beta.acquire();
DO $$
DECLARE p uuid; t uuid; c uuid; r record;
BEGIN
 SELECT proposal,ticket INTO STRICT p,t FROM beta.ui_draft(903,904,1,'A','weekly',current_date+2,'07:00','{0,15}');
 IF NOT beta.ui_finish(903,904,t,true,1) THEN RAISE EXCEPTION 'origin'; END IF;
 SELECT * INTO STRICT r FROM beta.ui_decide(903,904,p,1,true);
 IF r.status<>'active' THEN RAISE EXCEPTION 'initial proposal'; END IF;
 SELECT proposal,ticket INTO STRICT c,t FROM beta.ui_change_draft(903,904,2,p,'replace','B','daily',current_date+2,'08:00','{}');
 IF NOT beta.ui_finish(903,904,t,true,2) THEN RAISE EXCEPTION 'replacement receipt'; END IF;
 SELECT * INTO STRICT r FROM beta.ui_decide(903,904,c,2,true);
 IF r.status<>'replaced' THEN RAISE EXCEPTION 'replacement'; END IF;
 SELECT proposal,ticket INTO STRICT p,t FROM beta.ui_change_draft(903,904,3,c,'cancel',NULL,NULL,NULL,NULL,NULL);
 IF NOT beta.ui_finish(903,904,t,true,3) THEN RAISE EXCEPTION 'cancel preview'; END IF;
 SELECT * INTO STRICT r FROM beta.ui_decide(903,904,p,3,false);
 IF r.status<>'kept' THEN RAISE EXCEPTION 'decline cancellation'; END IF;
END $$;
SQL
[[ $(sql -c "SELECT count(*) FROM beta.proposal WHERE state='active' AND title='B'") == 1 ]]
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj /CN=synthetic -keyout "$tmp/key" -out "$tmp/cert" >/dev/null 2>&1
bash scripts/personal-archive.sh seal "$id" "$run" "$tmp" "$tmp/cert" "$(sha256sum < "$tmp/cert" | cut -d' ' -f1)" > "$tmp/result"
digest=$(python -c 'import json,sys;print(json.load(sys.stdin)["ciphertext_sha256"])' < "$tmp/result")
fresh
bash scripts/personal-archive.sh restore "$id" "$run" "$tmp/$digest.cms" "$digest" "$tmp/cert" "$tmp/key"
[[ $(sql -c "SELECT count(*) FROM beta.ui_call WHERE state='reserved'") == 0 ]]
[[ $(sql -c "SELECT count(*) FROM beta.proposal WHERE state='active' AND title='B'") == 1 ]]
[[ $(sql -c 'SET SESSION AUTHORIZATION personal_gateway; SELECT beta.acquire()') == f ]]
echo 'PASS replacement, declined cancellation, encrypted restore and old-approval fencing'
