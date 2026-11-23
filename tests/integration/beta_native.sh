#!/usr/bin/env bash
set -euo pipefail
: "${REV:?candidate SHA}" "${PG:?PG17 image ID}" "${APP:?accepted staging Python image ID}" "${N8N:?accepted n8n image ID}"
[[ $(git rev-parse HEAD) == "$REV" && -z $(git status --porcelain) ]]
[[ $(docker info --format '{{.ID}}') == 44c1ef83-c50e-4ecc-8f19-4b112bc40f29 ]]
for image in "$PG" "$APP" "$N8N"; do
  [[ $image =~ ^sha256:[a-f0-9]{64}$ && $(docker image inspect --format '{{.Id}}' "$image") == "$image" ]]
done
name="dincharya-beta-$(openssl rand -hex 12)"
net=$(docker network create --internal "$name")
containers=()
scratch=$(mktemp -d)
cleanup() {
  for id in "${containers[@]}"; do docker rm -fv "$id" >/dev/null; done
  docker network rm "$net" >/dev/null
  rm -rf -- "$scratch"
}
trap cleanup EXIT
git archive "$REV" -- dincharya prototypes/panchang telegram-gateway/lunar_handlers.py tests/integration/{m2g_bot,beta_relay_journey}.py workflows/m2g-lunar-acceptance.json staging/laptop/service.py | tar -x -C "$scratch"
chmod -R a+rX "$scratch"
export POSTGRES_PASSWORD=$(openssl rand -hex 32)
export BETA_GATEWAY_PASSWORD=$(openssl rand -hex 32)
db=$(docker run --pull never -d --network "$net" --network-alias db --tmpfs /var/lib/postgresql/data -e POSTGRES_PASSWORD -e POSTGRES_DB=dincharya_beta_rehearsal "$PG")
containers+=("$db")
sql=(docker exec -i "$db" psql -Xq -v ON_ERROR_STOP=1 -U postgres -d dincharya_beta_rehearsal)
for i in {1..60}; do
  if [[ $(docker exec "$db" cat /proc/1/comm) == postgres ]] && "${sql[@]}" -c 'SELECT 1' >/dev/null 2>&1; then break; fi
  sleep 1
done
"${sql[@]}" < database/personal_beta/0001_civil.sql
printf "ALTER ROLE beta_gateway LOGIN PASSWORD '%s';\n" "$BETA_GATEWAY_PASSWORD" | "${sql[@]}"
relay=$(docker run --pull never -d --network "$net" --network-alias relay --tmpfs /home/node/.n8n:uid=1000,gid=1000 -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_SECURE_COOKIE=false "$N8N")
containers+=("$relay")
docker run --rm --pull never --network "$net" --network-alias app -e BETA_GATEWAY_PASSWORD -e PYTHONPATH=/candidate -e PYTHONDONTWRITEBYTECODE=1 -v "$scratch:/candidate:ro" -w /candidate --entrypoint python "$APP" tests/integration/beta_relay_journey.py
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
recovery=$(docker run --pull never -d --network none --tmpfs /var/lib/postgresql/data -e POSTGRES_PASSWORD -e POSTGRES_DB=dincharya_beta_rehearsal "$PG" postgres -c listen_addresses=)
containers+=("$recovery")
for i in {1..60}; do
  if [[ $(docker exec "$recovery" cat /proc/1/comm) == postgres ]] && docker exec "$recovery" pg_isready -q; then break; fi
  sleep 1
done
docker exec "$recovery" psql -X -v ON_ERROR_STOP=1 -U postgres -d dincharya_beta_rehearsal -c 'CREATE ROLE beta_executor; CREATE ROLE beta_gateway; CREATE ROLE beta_worker; CREATE ROLE beta_operator'
docker exec -i "$recovery" pg_restore --exit-on-error --single-transaction -U postgres -d dincharya_beta_rehearsal < "$archive/restored.dump"
for table in authority proposal change_review occurrence slot attempt resolution; do
  query="COPY (SELECT to_jsonb(t)::text FROM beta.$table t ORDER BY 1) TO STDOUT"
  docker exec "$db" psql -XqAt -v ON_ERROR_STOP=1 -U postgres -d dincharya_beta_rehearsal -c "$query" > "$archive/original"
  docker exec "$recovery" psql -XqAt -v ON_ERROR_STOP=1 -U postgres -d dincharya_beta_rehearsal -c "$query" > "$archive/restored"
  cmp "$archive/original" "$archive/restored"
done
docker exec "$recovery" psql -Xq -v ON_ERROR_STOP=1 -U postgres -d dincharya_beta_rehearsal -c 'SELECT beta.fence_restore()'
echo 'PASS completed encrypted PG dump, independent networkless restore and seven table comparisons'
echo 'PASS native beta rehearsal, paired receipts, quarantine and restore fencing'
