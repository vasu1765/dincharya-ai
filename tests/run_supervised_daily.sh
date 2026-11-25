#!/usr/bin/env bash
set -euo pipefail
[[ $(git rev-parse HEAD) == "${REV:?reviewed revision}" && -z $(git status --porcelain) ]]
sha256sum -c docs/supervised-daily.sha256
sha256sum -c docs/personal-candidate.sha256
pg=sha256:ff87138949ad9a46f32ff23bd6852b52ce024a13dffe9b4087be98292cdd3b4f
app=sha256:fff0b1b58321339ad0de04804548cb8ff14c9a929e6eead08ce3cd96535493ca
umask 077
tmp=$(mktemp -d)
nonce=$(openssl rand -hex 16)
label="org.dincharya.supervised=$nonce"
net= db= svc=
inventory() { docker ps -aq --no-trunc | sort; docker volume ls -q | sort; docker network ls -q --no-trunc | sort; docker image ls -q --no-trunc | sort; }
inventory > "$tmp/before"
cleanup() {
  rc=$?
  cleanup_rc=0
  for id in "$svc" "$db"; do
    if [[ -n $id ]]; then
      [[ $(docker inspect -f '{{index .Config.Labels "org.dincharya.supervised"}}' "$id") == "$nonce" ]] && docker rm -fv "$id" >/dev/null || cleanup_rc=1
    fi
  done
  if [[ -n $net ]]; then docker network rm "$net" >/dev/null || cleanup_rc=1; fi
  inventory > "$tmp/after" && cmp -s "$tmp/before" "$tmp/after" || cleanup_rc=1
  rm -rf -- "$tmp"
  if (( cleanup_rc )); then
    echo "FAIL cleanup or inventory" >&2
    (( rc != 0 )) || rc=$cleanup_rc
  fi
  exit "$rc"
}
trap cleanup EXIT
mkdir "$tmp/repo" "$tmp/fixture"
git archive "$REV" | tar -x -C "$tmp/repo"
net=$(docker network create --internal --label "$label" "personal-$nonce")
export POSTGRES_PASSWORD=$(openssl rand -hex 32)
db=$(docker run --pull never -d --network "$net" --network-alias db --label "$label" --tmpfs /var/lib/postgresql/data -e POSTGRES_PASSWORD -e POSTGRES_DB=dincharya_personal_candidate "$pg")
unset POSTGRES_PASSWORD
sql() { docker exec -i "$db" psql -XqAt -U postgres -v ON_ERROR_STOP=1 -d dincharya_personal_candidate "$@"; }
ready=false
for _ in {1..60}; do
  if [[ $(docker exec "$db" cat /proc/1/comm) == postgres ]] && sql -c 'select 1' >/dev/null 2>&1; then ready=true; break; fi
  sleep 1
done
[[ $ready == true ]] || { echo "FAIL postgres_readiness" >&2; exit 1; }
source tests/personal_migration_diagnostic.sh
for f in database/personal/*.sql; do run_personal_migration "$f"; done
for r in personal_gateway personal_worker personal_operator; do
  key=$(openssl rand -hex 32)
  echo "$key" > "$tmp/fixture/$r.key"
  printf "ALTER ROLE %s LOGIN PASSWORD '%s';\n" "$r" "$key" | sql >/dev/null 2>&1 || { echo "FAIL scoped role setup" >&2; exit 1; }
done
unset key
sql -c "INSERT INTO beta.authority(singleton,recipient,bot,enabled,lookback) VALUES(true,903,904,true,interval '5 minutes')"
echo '{"owner":903,"bot":904}' > "$tmp/fixture/recording.json"
svc=$(docker run --pull never --label "$label" --network "$net" --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges --read-only -v "$tmp/repo:/repo:ro" -v "$tmp/fixture:/fixture" -w /repo -e PYTHONPATH=/repo -e PYTHONDONTWRITEBYTECODE=1 --entrypoint sleep -d "$app" 900)
docker exec "$svc" python tests/daily_sdk_delta.py
python3 tests/supervised_daily_delta.py "$db" "$svc"
