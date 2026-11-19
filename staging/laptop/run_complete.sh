#!/usr/bin/env bash
# Run from the clean, independently pinned PR checkout on the accepted WSL daemon.
set -euo pipefail
: "${REV:?reviewed revision}" "${PY:?accepted WSL Python}" "${KERNEL:?verified public DE440s path}"
if env | cut -d= -f1 | grep -Eq '^(DOCKER_|COMPOSE_|DINCHARYA_STAGE1_RECHECK$)'; then
  echo 'Conflicting context or project override' >&2
  exit 1
fi
export DINCHARYA_STAGE1_COMPLETE=1 PYTHONDONTWRITEBYTECODE=1
daemon=44c1ef83-c50e-4ecc-8f19-4b112bc40f29
parent=sha256:fff0b1b58321339ad0de04804548cb8ff14c9a929e6eead08ce3cd96535493ca
project=dincharya-stage1-complete
test "$(git rev-parse HEAD)" = "$REV"
test -z "$(git status --porcelain)"
test "$(docker info --format '{{.ID}}')" = "$daemon"
test "$(docker image inspect --format '{{.Id}}' "$parent")" = "$parent"
test ! -e "$HOME/.local/state/$project"
test -z "$(docker ps -aq --filter "label=com.docker.compose.project=$project")"
test -z "$(docker network ls -q --filter "name=^${project}_default$")"
test -z "$(docker volume ls -q --filter "label=com.docker.compose.project=$project")"
inventory() {
  for prior in dincharya-laptop-staging dincharya-stage1-recheck; do
    docker ps -a --filter "label=com.docker.compose.project=$prior" --format '{{.ID}} {{.State}}' | sort
    docker volume ls --filter "label=com.docker.compose.project=$prior" -q | sort
  done
}
before=$(inventory)
accepted_image() {
  local cid
  cid=$(docker ps -aq --filter label=com.docker.compose.project=dincharya-laptop-staging --filter "label=com.docker.compose.service=$1")
  test -n "$cid" && [[ "$cid" != *$'\n'* ]] || return 1
  docker inspect --format '{{.Image}}' "$cid"
}
pg=$(accepted_image db)
relay=$(accepted_image relay)
ctx=$(mktemp -d)
tag="dincharya-stage1-base:$(basename "$ctx" | tr '[:upper:]' '[:lower:]')"
docker tag "$parent" "$tag"
test "$(docker image inspect --format '{{.Id}}' "$tag")" = "$parent"
git show "$REV:staging/laptop/service.py" >"$ctx/service.py"
printf 'ARG BASE\nFROM ${BASE}\nCOPY service.py /src/staging/laptop/service.py\n' >"$ctx/Dockerfile"
docker build --network none --pull=false --build-arg "BASE=$tag" --iidfile "$ctx/id" "$ctx"
stage() { "$PY" -B staging/laptop/control.py "$1" --daemon "$daemon" --revision "$REV" "${@:2}"; }
stage prepare --db "$pg" --relay "$relay" --app "$(cat "$ctx/id")" --kernel "$KERNEL"
finish() {
  local result=$? stopped=0
  trap - EXIT
  stage stop || stopped=$?
  printf 'journey_exit=%d stop_exit=%d\n' "$result" "$stopped"
  test "$before" = "$(inventory)" || exit 1
  test "$stopped" = 0 || exit 1
  exit "$result"
}
trap finish EXIT
stage initialize
stage start
"$PY" -B staging/laptop/complete.py "$REV" "$daemon" "$pg"
