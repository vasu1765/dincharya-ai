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
: "${REV:?candidate SHA}" "${PG:?PG17 image ID}" "${APP:?accepted staging Python image ID}"
[[ $(git rev-parse HEAD) == "$REV" && -z $(git status --porcelain) ]]
[[ $(docker info --format '{{.ID}}') == 44c1ef83-c50e-4ecc-8f19-4b112bc40f29 ]]
read -r expected_pg expected_app expected_n8n < <(python3 -B -c 'from dincharya.attended_runtime import PG,APP,N8N;print(PG,APP,N8N)')
[[ $PG == "$expected_pg" && $APP == "$expected_app" && ${N8N:?} == "$expected_n8n" ]]
for image in "$PG" "$APP" "${N8N:?pinned n8n image ID}"; do
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
    LC_ALL=C sed -nE '/^FAIL substage=[a-z_]+ exception=[A-Za-z_]+( sqlstate=[[:alnum:]]{5})?$/p; /^DIAGNOSTIC sent_count=[0-9]+ last_text_matches_fixture=(True|False)$/p' "$diagnostic" >&3
    LC_ALL=C sed -nE '/^OPERATOR_FAIL step=[a-z_]+ class=[A-Za-z]+ http=[0-9]{1,3}( site=[a-z_]+\.py:[0-9]+)?$/p' "$diagnostic" >&3
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
stage public_ephemeris
: "${KERNEL:?exact path to previously verified public de440s.bsp}"
[[ -f $KERNEL && $KERNEL = /* ]]
kernel_pin=$(python3 -c 'import json; print(json.load(open("prototypes/panchang/ephemeris.json"))["sha256"])')
[[ $(sha256sum "$KERNEL" | cut -d' ' -f1) == "$kernel_pin" ]]
export kernel_pin
stage astronomy_dependency
: "${CERTIFI_WHEEL:?absolute path to the reviewed certifi 2025.10.5 wheel}"
[[ $CERTIFI_WHEEL = /* && -f $CERTIFI_WHEEL ]]
wheel_name=certifi-2025.10.5-py3-none-any.whl
wheel_pin=$(python3 -c 'import json,sys; print(next(w["sha256"] for w in json.load(open("prototypes/panchang/ephemeris.json"))["wheel_artifacts"] if w["filename"] == sys.argv[1]))' "$wheel_name")
# Stage and verify the bytes that the recording-only application imports.
cp -- "$CERTIFI_WHEEL" "$scratch/$wheel_name"
[[ $(sha256sum "$scratch/$wheel_name" | cut -d' ' -f1) == "$wheel_pin" ]]
stage network_create
net=$(docker network create --internal --label "$label" "$name")
stage source_archive
git archive "$REV" -- dincharya prototypes/panchang tests/integration/operator_path.py tests/test_attended_trust.py tests/integration/beta_relay_journey.py workflows/m2g-lunar-acceptance.json | tar -x -C "$scratch"
chmod -R a+rX "$scratch"
mode=operator
  stage "${mode}_start"
  POSTGRES_PASSWORD=$(openssl rand -hex 32)
  POLLER_PASSWORD=$(openssl rand -hex 32)
  WORKER_PASSWORD=$(openssl rand -hex 32)
  export POSTGRES_PASSWORD POLLER_PASSWORD WORKER_PASSWORD
  db=$(docker run --label "$label" --pull never -d --network "$net" --network-alias db --tmpfs /var/lib/postgresql/data -e POSTGRES_PASSWORD -e POSTGRES_DB=dincharya_attended_test "$PG")
  sql=(docker exec -i "$db" psql -XqAt -v VERBOSITY=verbose -v ON_ERROR_STOP=1 -U postgres -d dincharya_attended_test)
  ready=false
  for i in {1..60}; do
    if [[ $(docker exec "$db" cat /proc/1/comm) == postgres ]] && "${sql[@]}" -c 'SELECT 1' >/dev/null 2>&1; then ready=true; break; fi
    sleep 1
  done
  [[ $ready == true ]]
  stage "${mode}_bootstrap"
  "${sql[@]}" -f - <database/attended/0001_disposable.sql
  printf "ALTER ROLE attended_poller LOGIN PASSWORD '%s'; ALTER ROLE attended_worker LOGIN PASSWORD '%s';" "$POLLER_PASSWORD" "$WORKER_PASSWORD" | "${sql[@]}" -f -
  "${sql[@]}" -f - <database/attended/0002_operator.sql
  stage relay_start
  docker run --label "$label" --pull never -d --network "$net" --network-alias relay --tmpfs /home/node/.n8n:uid=1000,gid=1000 -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_SECURE_COOKIE=false -e EXECUTIONS_DATA_SAVE_ON_SUCCESS=none -e EXECUTIONS_DATA_SAVE_ON_ERROR=none "$N8N" >/dev/null
  stage manifest
  export PG APP N8N REV
  python3 - "$scratch/manifest.json" <<'PYTHON'
import json, os,sys,time
from datetime import datetime
from zoneinfo import ZoneInfo
start=int(time.time())-1
def slot(label,delay):
    t=datetime.fromtimestamp(start+delay,ZoneInfo("Asia/Kolkata"))
    return "Schedule "+label+" on "+t.strftime("%Y-%m-%d at %H:%M")
with open(sys.argv[1],"w") as f:
    json.dump(dict(sha=os.environ["REV"],host="operator-fixture",pg=os.environ["PG"],app=os.environ["APP"],
        n8n=os.environ["N8N"],bot=93002,owner=93001,start=start,end=start+600,silent=slot("Quiet",360),
        reminder=slot("Reminder",240),question="What was the tithi on 2023-12-06?",kernel_sha256=os.environ["kernel_pin"]),f)
PYTHON
  chmod 444 "$scratch/manifest.json"
  pin=$(sha256sum "$scratch/manifest.json" | cut -d' ' -f1)
  start=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["start"])' "$scratch/manifest.json")
  "${sql[@]}" -c "INSERT INTO attended.session VALUES(true,93001,93002,to_timestamp($start),to_timestamp($start+600),true); INSERT INTO attended.operator_approval(singleton,digest) VALUES(true,'$pin')"
  stage synthetic_runtime_files
  mkdir "$resources/session"
  cp "$scratch/manifest.json" "$resources/session/"
  printf '%s' "$REV" > "$resources/session/revision"
  printf '%s' "$POLLER_PASSWORD" > "$resources/session/poller.key"
  printf '%s' "$WORKER_PASSWORD" > "$resources/session/worker.key"
  printf '93002:%032d' 0 > "$resources/session/bot.key"
  openssl rand -hex 32 > "$resources/session/relay.key"
  # Fixture keys are disposable. Restrict the host parent and grant the app UID access.
  touch "$resources/session/de440s.bsp" "$resources/session/$wheel_name"
  chmod 755 "$resources/session"
  chmod 444 "$resources/session/"*
  stage operator_loop
  docker run --label "$label" --rm --pull never --network "$net" --network-alias app --hostname operator-fixture --read-only -e TMPDIR=/tmp --tmpfs /tmp:mode=1777 -e REV -e PYTHONPATH=/candidate -v "$resources/session:/run/attended:ro" --mount "type=bind,src=$scratch/$wheel_name,dst=/run/attended/$wheel_name,readonly" -e PYTHONDONTWRITEBYTECODE=1 --mount "type=bind,src=$KERNEL,dst=/run/attended/de440s.bsp,readonly" -v "$scratch:/candidate:ro" -w /candidate --entrypoint python "$APP" tests/integration/operator_path.py
  stage operator_evidence
  [[ $("${sql[@]}" -c "SELECT string_agg(kind,',' ORDER BY ordinal) FROM attended.attempt WHERE status='sent' AND chat=93001 AND message>0") == historical,preview,decision,preview,decision,reminder ]]
  [[ $("${sql[@]}" -c "SELECT consumed FROM attended.operator_approval") == t ]]
  echo "PASS consumed approval and six paired receipts"
