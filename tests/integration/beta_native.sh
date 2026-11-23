#!/usr/bin/env bash
set -euo pipefail
: "${REV:?candidate SHA}" "${PG:?PG17 image ID}" "${APP:?accepted staging Python image ID}" "${N8N:?accepted n8n image ID}"
[[ $(git rev-parse HEAD) == "$REV" && -z $(git status --porcelain) ]]
[[ $(docker info --format '{{.ID}}') == 44c1ef83-c50e-4ecc-8f19-4b112bc40f29 ]]
for image in "$PG" "$APP" "$N8N"; do
  [[ $image =~ ^sha256:[a-f0-9]{64}$ && $(docker image inspect --format '{{.Id}}' "$image") == "$image" ]]
done
name="dincharya-beta-$(openssl rand -hex 12)"
scratch=$(mktemp -d)
resources=$(mktemp -d)
inventory() {
  local destination=$1
  docker ps -a --no-trunc --format '{{.ID}} {{.State}}' | LC_ALL=C sort > "$destination/containers" &&
  docker network ls --no-trunc -q | LC_ALL=C sort > "$destination/networks" &&
  docker volume ls -q | LC_ALL=C sort > "$destination/volumes" &&
  docker image ls --no-trunc --format '{{.ID}} {{.Repository}}:{{.Tag}}' | LC_ALL=C sort > "$destination/images"
}
mkdir "$resources/before" "$resources/after"
inventory "$resources/before"
label="org.dincharya.beta.run=$name"
cleanup() {
  local original=$? failed=0 owned
  trap - EXIT
  set +e
  owned=$(docker ps -aq --filter "label=$label") || failed=1
  for id in $owned; do docker rm -fv "$id" >/dev/null || failed=1; done
  owned=$(docker network ls -q --filter "label=$label") || failed=1
  for id in $owned; do docker network rm "$id" >/dev/null || failed=1; done
  inventory "$resources/after" || failed=1
  for kind in containers networks volumes images; do
    cmp -s "$resources/before/$kind" "$resources/after/$kind" || { echo "FAIL inventory $kind" >&2; failed=1; }
  done
  rm -rf -- "$scratch" "$resources" || failed=1
  if (( original != 0 )); then exit "$original"; fi
  if (( failed )); then exit 1; fi
  echo 'PASS cleanup and unchanged Docker inventory'
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
net=$(docker network create --internal --label "$label" "$name")
git archive "$REV" -- dincharya prototypes/panchang telegram-gateway/lunar_handlers.py tests/integration/{m2g_bot,beta_relay_journey}.py workflows/m2g-lunar-acceptance.json staging/laptop/service.py | tar -x -C "$scratch"
chmod -R a+rX "$scratch"
export POSTGRES_PASSWORD=$(openssl rand -hex 32)
export BETA_GATEWAY_PASSWORD=$(openssl rand -hex 32)
db=$(docker run --label "$label" --pull never -d --network "$net" --network-alias db --tmpfs /var/lib/postgresql/data -e POSTGRES_PASSWORD -e POSTGRES_DB=dincharya_beta_rehearsal "$PG")
sql=(docker exec -i "$db" psql -Xq -v ON_ERROR_STOP=1 -U postgres -d dincharya_beta_rehearsal)
for i in {1..60}; do
  if [[ $(docker exec "$db" cat /proc/1/comm) == postgres ]] && "${sql[@]}" -c 'SELECT 1' >/dev/null 2>&1; then break; fi
  sleep 1
done
"${sql[@]}" < database/personal_beta/0001_civil.sql
printf "ALTER ROLE beta_gateway LOGIN PASSWORD '%s';\n" "$BETA_GATEWAY_PASSWORD" | "${sql[@]}"
relay=$(docker run --label "$label" --pull never -d --network "$net" --network-alias relay --tmpfs /home/node/.n8n:uid=1000,gid=1000 -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_SECURE_COOKIE=false "$N8N")
docker run --label "$label" --rm --pull never --network "$net" --network-alias app -e BETA_GATEWAY_PASSWORD -e PYTHONPATH=/candidate -e PYTHONDONTWRITEBYTECODE=1 -v "$scratch:/candidate:ro" -w /candidate --entrypoint python "$APP" tests/integration/beta_relay_journey.py
"${sql[@]}" < tests/integration/beta_native.sql
# Verify an actual completed dump before sealing or restoring anything.
archive=$(mktemp -d "$scratch/archives.XXXXXXXX")
docker exec "$db" pg_dump -Fc -U postgres -d dincharya_beta_rehearsal > "$archive/input.dump"
openssl req -newkey rsa:2048 -nodes -x509 -days 1 -subj /CN=fixture -keyout "$archive/key" -out "$archive/cert" 2>/dev/null
cert_sha=$(sha256sum "$archive/cert" | cut -d' ' -f1)
manifest=$(python3 -B -m dincharya.beta_archive "$archive" "$archive/cert" "$cert_sha" < "$archive/input.dump")
digest=$(python3 -c 'import json,sys;print(json.load(sys.stdin)["ciphertext_sha256"])' <<<"$manifest")
[[ $(sha256sum "$archive/$digest.cms" | cut -d' ' -f1) == "$digest" ]]
openssl cms -decrypt -binary -inform DER -inkey "$archive/key" -in "$archive/$digest.cms" -out "$archive/restored.dump"
cmp "$archive/input.dump" "$archive/restored.dump"
recovery=$(docker run --label "$label" --pull never -d --network none --tmpfs /var/lib/postgresql/data -e POSTGRES_PASSWORD -e POSTGRES_DB=dincharya_beta_rehearsal "$PG" postgres -c listen_addresses=)
for i in {1..60}; do
  if [[ $(docker exec "$recovery" cat /proc/1/comm) == postgres ]] && docker exec "$recovery" pg_isready -q; then break; fi
  sleep 1
done
docker exec "$recovery" psql -X -v ON_ERROR_STOP=1 -U postgres -d dincharya_beta_rehearsal -c 'CREATE ROLE beta_executor; CREATE ROLE beta_gateway; CREATE ROLE beta_worker; CREATE ROLE beta_operator'
docker exec -i "$recovery" pg_restore --exit-on-error --single-transaction -U postgres -d dincharya_beta_rehearsal < "$archive/restored.dump"
for table in authority proposal change_review occurrence slot attempt receipt_evidence reconcile_permit resolution; do
  query="COPY (SELECT to_jsonb(t)::text FROM beta.$table t ORDER BY 1) TO STDOUT"
  docker exec "$db" psql -XqAt -v ON_ERROR_STOP=1 -U postgres -d dincharya_beta_rehearsal -c "$query" > "$archive/original"
  docker exec "$recovery" psql -XqAt -v ON_ERROR_STOP=1 -U postgres -d dincharya_beta_rehearsal -c "$query" > "$archive/restored"
  cmp "$archive/original" "$archive/restored"
done
docker exec "$recovery" psql -Xq -v ON_ERROR_STOP=1 -U postgres -d dincharya_beta_rehearsal -c 'SELECT beta.fence_restore()'
echo 'PASS completed encrypted PG dump, independent networkless restore and nine table comparisons'
echo 'PASS native beta rehearsal, paired receipts, quarantine and restore fencing'
