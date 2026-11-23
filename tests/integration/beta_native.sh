#!/usr/bin/env bash
set +x
set -euo pipefail
umask 077
exec 3>&2
diagnostic=
current_stage=preflight
stage() {
  current_stage=$1
  if [[ -n ${diagnostic:-} && -f $diagnostic ]]; then : > "$diagnostic"; fi
  printf 'STAGE %s\n' "$current_stage" >&3
}
stage preflight
trap 'rc=$?; if (( rc )); then printf "FAIL stage=%s exit=%d\n" "$current_stage" "$rc" >&3; fi' EXIT
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
# Keep raw diagnostics outside the container mount. Report only SQLSTATE and
# the numeric input line from verbose psql, never error text or SQL values.
diagnostic=$resources/stderr
exec 2>>"$diagnostic"
# No Docker resources exist until the inventory is complete.
trap 'rc=$?; if (( rc )); then printf "FAIL stage=%s exit=%d\n" "$current_stage" "$rc" >&3; fi; rm -rf -- "$scratch" "$resources"; exit "$rc"' EXIT
stage inventory_before
mkdir "$resources/before" "$resources/after"
inventory "$resources/before"
label="org.dincharya.beta.run=$name"
cleanup() {
  local original=$? failed=0 owned
  trap - EXIT
  set +e
  if (( original )); then
    printf 'FAIL stage=%s exit=%d' "$current_stage" "$original" >&3
    LC_ALL=C sed -nE '/^(psql:<stdin>:[0-9]+: )?(ERROR|FATAL|PANIC):  [0-9A-Z]{5}:/{s/^(psql:<stdin>:([0-9]+): )?(ERROR|FATAL|PANIC):  ([0-9A-Z]{5}):.*/ sqlstate=\4 input_line=\2/p;q;}' "$diagnostic" | tr -d '\n' >&3
    printf '\n' >&3
  fi
  stage cleanup
  owned=$(docker ps -aq --filter "label=$label") || failed=1
  for id in $owned; do docker rm -fv "$id" >/dev/null || failed=1; done
  owned=$(docker network ls -q --filter "label=$label") || failed=1
  for id in $owned; do docker network rm "$id" >/dev/null || failed=1; done
  inventory "$resources/after" || failed=1
  for kind in containers networks volumes images; do
    cmp -s "$resources/before/$kind" "$resources/after/$kind" || { echo "FAIL inventory $kind" >&3; failed=1; }
  done
  rm -rf -- "$scratch" "$resources" || failed=1
  if (( failed )); then echo "FAIL cleanup or inventory" >&3; else echo "PASS cleanup and unchanged Docker inventory" >&3; fi
  if (( original != 0 )); then exit "$original"; fi
  if (( failed )); then exit 1; fi
  return 0
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
stage network_create
net=$(docker network create --internal --label "$label" "$name")
stage source_archive
git archive "$REV" -- dincharya prototypes/panchang telegram-gateway/lunar_handlers.py tests/integration/{m2g_bot,beta_relay_journey}.py workflows/m2g-lunar-acceptance.json staging/laptop/service.py | tar -x -C "$scratch"
chmod -R a+rX "$scratch"
stage synthetic_role_secrets
POSTGRES_PASSWORD=$(openssl rand -hex 32)
BETA_GATEWAY_PASSWORD=$(openssl rand -hex 32)
export POSTGRES_PASSWORD BETA_GATEWAY_PASSWORD
stage postgres_start
db=$(docker run --label "$label" --pull never -d --network "$net" --network-alias db --tmpfs /var/lib/postgresql/data -e POSTGRES_PASSWORD -e POSTGRES_DB=dincharya_beta_rehearsal "$PG")
stage postgres_readiness
sql=(docker exec -i "$db" psql -Xq -v VERBOSITY=verbose -v ON_ERROR_STOP=1 -U postgres -d dincharya_beta_rehearsal)
ready=false
for i in {1..60}; do
  if [[ $(docker exec "$db" cat /proc/1/comm) == postgres ]] && "${sql[@]}" -c 'SELECT 1' >/dev/null 2>&1; then ready=true; break; fi
  sleep 1
done
[[ $ready == true ]]
stage schema_bootstrap
"${sql[@]}" -f - >/dev/null < database/personal_beta/0001_civil.sql
stage gateway_role_setup
printf "ALTER ROLE beta_gateway LOGIN PASSWORD '%s';\n" "$BETA_GATEWAY_PASSWORD" | "${sql[@]}" -f - >/dev/null
stage n8n_start
relay=$(docker run --label "$label" --pull never -d --network "$net" --network-alias relay --tmpfs /home/node/.n8n:uid=1000,gid=1000 -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_SECURE_COOKIE=false "$N8N")
stage signed_relay_journey
docker run --label "$label" --rm --pull never --network "$net" --network-alias app -e BETA_GATEWAY_PASSWORD -e PYTHONPATH=/candidate -e PYTHONDONTWRITEBYTECODE=1 -v "$scratch:/candidate:ro" -w /candidate --entrypoint python "$APP" tests/integration/beta_relay_journey.py >/dev/null
stage sql_assertions
"${sql[@]}" -f - >/dev/null < tests/integration/beta_native.sql
# Verify an actual completed dump before sealing or restoring anything.
stage pg_dump
archive=$(mktemp -d "$scratch/archives.XXXXXXXX")
docker exec "$db" pg_dump -Fc -U postgres -d dincharya_beta_rehearsal > "$archive/input.dump"
stage cms_recipient
openssl req -newkey rsa:2048 -nodes -x509 -days 1 -subj /CN=fixture -keyout "$archive/key" -out "$archive/cert" 2>/dev/null
cert_sha=$(sha256sum "$archive/cert" | cut -d' ' -f1)
stage cms_encrypt
manifest=$(python3 -B -m dincharya.beta_archive "$archive" "$archive/cert" "$cert_sha" < "$archive/input.dump")
stage ciphertext_verify
digest=$(python3 -c 'import json,sys;print(json.load(sys.stdin)["ciphertext_sha256"])' <<<"$manifest")
[[ $(sha256sum "$archive/$digest.cms" | cut -d' ' -f1) == "$digest" ]]
stage cms_decrypt
openssl cms -decrypt -binary -inform DER -inkey "$archive/key" -in "$archive/$digest.cms" -out "$archive/restored.dump"
cmp "$archive/input.dump" "$archive/restored.dump"
stage restore_postgres_start
recovery=$(docker run --label "$label" --pull never -d --network none --tmpfs /var/lib/postgresql/data -e POSTGRES_PASSWORD -e POSTGRES_DB=dincharya_beta_rehearsal "$PG" postgres -c listen_addresses=)
stage restore_readiness
ready=false
for i in {1..60}; do
  if [[ $(docker exec "$recovery" cat /proc/1/comm) == postgres ]] && docker exec "$recovery" pg_isready -q; then ready=true; break; fi
  sleep 1
done
[[ $ready == true ]]
stage restore_roles
docker exec "$recovery" psql -X -v VERBOSITY=verbose -v ON_ERROR_STOP=1 -U postgres -d dincharya_beta_rehearsal -c 'CREATE ROLE beta_executor; CREATE ROLE beta_gateway; CREATE ROLE beta_worker; CREATE ROLE beta_operator'
stage restore_archive
docker exec -i "$recovery" pg_restore --exit-on-error --single-transaction -U postgres -d dincharya_beta_rehearsal < "$archive/restored.dump"
for table in authority proposal change_review occurrence slot attempt receipt_evidence reconcile_permit resolution; do
  stage "read_source_$table"
  query="COPY (SELECT to_jsonb(t)::text FROM beta.$table t ORDER BY 1) TO STDOUT"
  docker exec "$db" psql -XqAt -v VERBOSITY=verbose -v ON_ERROR_STOP=1 -U postgres -d dincharya_beta_rehearsal -c "$query" > "$archive/original"
  stage "read_restored_$table"
  docker exec "$recovery" psql -XqAt -v VERBOSITY=verbose -v ON_ERROR_STOP=1 -U postgres -d dincharya_beta_rehearsal -c "$query" > "$archive/restored"
  stage "compare_$table"
  cmp "$archive/original" "$archive/restored"
done
stage restore_fence
docker exec "$recovery" psql -Xq -v VERBOSITY=verbose -v ON_ERROR_STOP=1 -U postgres -d dincharya_beta_rehearsal -c 'SELECT beta.fence_restore()'
echo 'PASS completed encrypted PG dump, independent networkless restore and nine table comparisons'
echo 'PASS native beta rehearsal, paired receipts, quarantine and restore fencing'
