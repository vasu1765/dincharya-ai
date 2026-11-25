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
for image in "$PG" "$APP"; do
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
git archive "$REV" -- dincharya prototypes/panchang tests/integration/attended_delta.py | tar -x -C "$scratch"
chmod -R a+rX "$scratch"
for mode in appointments budget loss crash disabled expired; do
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
  "${sql[@]}" -c "INSERT INTO attended.session VALUES(true,93001,93002,now(),now()+interval '20 minutes',true)"
  export EXPIRED_ID=11111111-1111-4111-8111-111111111111
  if [[ $mode == disabled ]]; then
    "${sql[@]}" -c "UPDATE attended.session SET enabled=false"
  elif [[ $mode == expired ]]; then
    "${sql[@]}" -c "INSERT INTO attended.proposal(id,update_id,title,due,remind,expires) VALUES('$EXPIRED_ID',1,'Fixture',now()+interval '1 minute',false,now()-interval '1 second'); INSERT INTO attended.attempt(ordinal,proposal,kind,status,chat,message) VALUES(1,'$EXPIRED_ID','preview','sent',93001,1)"
  fi
  stage "${mode}_journey"
  docker run --label "$label" --rm --pull never --network "$net" -e POLLER_PASSWORD -e WORKER_PASSWORD -e EXPIRED_ID -e PYTHONPATH=/candidate -e PYTHONDONTWRITEBYTECODE=1 -v "$scratch:/candidate:ro" -w /candidate --entrypoint python "$APP" tests/integration/attended_delta.py "$mode"
  stage "${mode}_evidence"
  case $mode in
    appointments) expected='5|5|1|2';;
    budget) expected='6|6|0|0';;
    disabled) expected='0|0|0|0';;
    expired) expected='1|1|0|0';;
    crash|loss) expected='1|0|0|0';;
  esac
  [[ $("${sql[@]}" -c "SELECT count(*),count(*) FILTER(WHERE status='sent' AND chat=93001 AND message>0),count(*) FILTER(WHERE kind='reminder'),(SELECT count(*) FROM attended.proposal WHERE state='confirmed') FROM attended.attempt") == "$expected" ]]
  if [[ $mode == crash || $mode == loss ]]; then
    [[ $("${sql[@]}" -c "SELECT status FROM attended.attempt") == uncertain ]]
  fi
  docker rm -fv "$db" >/dev/null
  echo "PASS $mode evidence $expected"
done
