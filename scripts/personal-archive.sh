#!/usr/bin/env bash
# Fresh, networkless fixture containers only. No host backup transfer.
set -euo pipefail
umask 077
action=${1:?seal or restore}
id=${2:?full container ID}
run=${3:?fixture label nonce}
[[ "$id" =~ ^[0-9a-f]{64}$ && "$run" =~ ^[0-9a-f]{32}$ ]]
expected='sha256:ff87138949ad9a46f32ff23bd6852b52ce024a13dffe9b4087be98292cdd3b4f'
[[ $(docker inspect -f '{{.Image}} {{.HostConfig.NetworkMode}} {{index .Config.Labels "org.dincharya.personal-fixture"}}' "$id") == "$expected none $run" ]]
docker inspect -f '{{json .HostConfig.Tmpfs}} {{json .Mounts}}' "$id" | python -c '
import json, sys
line = sys.stdin.read().strip()
tmpfs, end = json.JSONDecoder().raw_decode(line)
mounts = json.loads(line[end:].strip())
if set(tmpfs or {}) != {"/var/lib/postgresql/data"} or any(
    m["Type"] != "tmpfs" or m["Destination"] != "/var/lib/postgresql/data" for m in mounts or []
):
    sys.exit("Only the fixture data tmpfs is permitted")
' 
db=dincharya_personal_candidate
sql() { docker exec -i "$id" psql -XqAt -v ON_ERROR_STOP=1 -U postgres -d "$db" "$@"; }
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
case "$action" in
seal)
  [[ $# == 6 ]]
  docker exec "$id" pg_dump -Fc -U postgres "$db" > "$tmp/data"
  docker exec -i "$id" pg_restore -l < "$tmp/data" > /dev/null
  python -m dincharya.beta_archive "$4" "$5" "$6" < "$tmp/data"
  ;;
restore)
  [[ $# == 7 && "$5" =~ ^[0-9a-f]{64}$ && $(sha256sum < "$4" | cut -d' ' -f1) == "$5" ]]
  [[ $(sql -c "SELECT count(*) FROM pg_namespace WHERE nspname NOT IN ('public','information_schema') AND nspname !~ '^pg_'") == 0 ]]
  [[ $(sql -c "SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace") == 0 ]]
  openssl cms -decrypt -binary -inform DER -in "$4" -recip "$6" -inkey "$7" -out "$tmp/data"
  docker exec -i "$id" pg_restore -l < "$tmp/data" > /dev/null
  sql -c 'BEGIN; CREATE ROLE personal_executor NOLOGIN; CREATE ROLE personal_gateway NOLOGIN; CREATE ROLE personal_worker NOLOGIN; CREATE ROLE personal_operator NOLOGIN; COMMIT'
  docker exec -i "$id" pg_restore -e -1 -U postgres -d "$db" < "$tmp/data"
  sql -c 'BEGIN; REVOKE ALL ON DATABASE dincharya_personal_candidate FROM PUBLIC; GRANT CONNECT ON DATABASE dincharya_personal_candidate TO personal_gateway,personal_worker,personal_operator; SELECT beta.fence_restore(); COMMIT'
  [[ $(sql -c 'SELECT count(*) FROM beta.authority WHERE enabled') == 0 ]]
  ;;
*) exit 2 ;;
esac
