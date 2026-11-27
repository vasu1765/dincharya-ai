#!/usr/bin/env bash
# Restore rehearsal only. Refuse every connected or persistent target.
set -euo pipefail
umask 077
id=${1:?full container ID}
archive=${2:?approved ciphertext}
digest=${3:?independently retained SHA256}
cert=${4:?recipient PEM}
key=${5:?recovery key}
[[ $id =~ ^[0-9a-f]{64}$ && $digest =~ ^[0-9a-f]{64}$ ]]
docker inspect "$id" | python3 -c '
import json,sys
c,=json.load(sys.stdin)
h=c["HostConfig"]
ok=(c["Image"]=="sha256:ff87138949ad9a46f32ff23bd6852b52ce024a13dffe9b4087be98292cdd3b4f"
 and c["Config"]["Labels"].get("org.dincharya.restore")=="daily-isolated"
 and h["NetworkMode"]=="none" and set(h.get("Tmpfs") or {})=={"/var/lib/postgresql/data"}
 and all(m["Type"]=="tmpfs" and m["Destination"]=="/var/lib/postgresql/data" for m in c["Mounts"]))
if not ok: sys.exit("Restore target refused")'
sql() { docker exec -i "$id" psql -XqAt -U postgres -v ON_ERROR_STOP=1 -d dincharya_personal_candidate "$@"; }
[[ $(sql -c "SELECT count(*) FROM pg_namespace WHERE nspname NOT IN ('public','information_schema') AND nspname !~ '^pg_'") == 0 ]]
[[ $(sql -c "SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace") == 0 ]]
# Fail closed rather than placing a plaintext database dump in the default /tmp.
[[ $(findmnt -n -M /dev/shm -o FSTYPE) == tmpfs ]]
tmp=$(mktemp -d /dev/shm/dincharya-daily.XXXXXXXX)
trap 'rm -rf -- "$tmp"' EXIT
# Authenticate the exact private copy passed to OpenSSL.
[[ -f "$archive" && ! -L "$archive" ]]
cp -- "$archive" "$tmp/ciphertext"
[[ $(sha256sum < "$tmp/ciphertext" | cut -d' ' -f1) == "$digest" ]]
openssl cms -decrypt -binary -inform DER -in "$tmp/ciphertext" -recip "$cert" -inkey "$key" -out "$tmp/dump"
docker exec -i "$id" pg_restore -l < "$tmp/dump" >/dev/null
sql -c 'BEGIN; CREATE ROLE personal_executor NOLOGIN; CREATE ROLE personal_gateway NOLOGIN; CREATE ROLE personal_worker NOLOGIN; CREATE ROLE personal_operator NOLOGIN; CREATE ROLE personal_observer NOLOGIN; CREATE ROLE personal_backup NOLOGIN; COMMIT'
docker exec -i "$id" pg_restore -e -1 -U postgres -d dincharya_personal_candidate < "$tmp/dump"
sql -c 'BEGIN; REVOKE ALL ON DATABASE dincharya_personal_candidate FROM PUBLIC; SELECT beta.fence_restore(); COMMIT'
[[ $(sql -c 'SELECT count(*) FROM beta.authority WHERE enabled') == 0 ]]
