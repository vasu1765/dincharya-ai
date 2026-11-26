#!/usr/bin/env bash
# Existing provisioned services only. No registration, volume creation or restart loop.
set -euo pipefail
mode=${3:-daily}
[[ "$mode" == daily || "$mode" == bounded ]]
rev=${1:?approved commit}
envfile=${2:?private compose env file}
[[ "$rev" =~ ^[0-9a-f]{40}$ && $(git rev-parse HEAD) == "$rev" && -z $(git status --porcelain) ]]
[[ "$envfile" == /* && ! -L "$envfile" && -f "$envfile" && -O "$envfile" && $(stat -c %a "$envfile") == 600 ]]
sha256sum --quiet -c docs/daily-release.sha256
host=$(docker info --format '{{.ID}}')
compose=(docker compose --env-file "$envfile" -f ops/daily-compose.yaml)
if [[ "$mode" == bounded ]]; then
  compose+=(-p dincharya-daily-bounded -f ops/daily-bounded.yaml)
fi
compose+=(--profile personal)
# Inspect resolved paths without sourcing arbitrary shell code or logging configuration.
config=$("${compose[@]}" config --format json)
source_dir=$(python3 -c 'import json,sys; print(next(v["source"] for v in json.load(sys.stdin)["services"]["operator"]["volumes"] if v["target"]=="/repo"))' <<< "$config")
root=$(python3 -c 'import json,sys; print(next(v["source"] for v in json.load(sys.stdin)["services"]["operator"]["volumes"] if v["target"]=="/run/daily"))' <<< "$config")
[[ -O "$root" && ! -L "$root" && $(stat -c %a "$root") == 700 && ! -e "$root/STOP" ]]
# Compare the entire mounted export with the approved Git tree. Refuse extra modules,
# symlinks or substituted scripts before any service receives credentials.
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
git archive "$rev" | tar -x -C "$tmp"
diff --no-dereference -qr "$tmp" "$source_dir" >/dev/null
python3 - "$root/approval.json" "$rev" "$host" "$mode" <<'PY'
import json,sys
from pathlib import Path
a=json.loads(Path(sys.argv[1]).read_bytes())
if (a.get('revision'),a.get('host'),a.get('profile'))!=tuple(sys.argv[2:]):
    raise SystemExit('Host, revision or persistent approval mismatch')
PY
# Start only previously provisioned containers, after the revision and host checks.
for entry in 'db sha256:ff87138949ad9a46f32ff23bd6852b52ce024a13dffe9b4087be98292cdd3b4f dincharya_personal_pg17 /var/lib/postgresql/data' 'relay sha256:6723b440354bb8e1395a1ecee12685fe03923f897bf6e4d5bb2c6c2bd2051697 dincharya_personal_n8n /home/node/.n8n'; do
  read -r service image volume target <<< "$entry"
  id=$("${compose[@]}" ps -aq "$service")
  [[ -n "$id" ]]
  docker inspect "$id" | python3 -c '
import json,sys
c,=json.load(sys.stdin)
image,volume,target,mode=sys.argv[1:]
if c["Image"]!=image or c["HostConfig"].get("PortBindings") or not any(
    m["Destination"]==target and ((mode=="daily" and m["Type"]=="volume" and m["Name"]==volume) or (mode=="bounded" and m["Type"]=="tmpfs")) for m in c["Mounts"]):
    sys.exit("Unexpected provisioned service")
if mode=="bounded" and any(m["Type"]=="volume" for m in c["Mounts"]):
    sys.exit("Persistent mount on bounded fixture")
' "$image" "$volume" "$target" "$mode"
done
"${compose[@]}" start db relay
ready=false
for _ in {1..30}; do
  db=$("${compose[@]}" ps -q db)
  if [[ -n "$db" && $(docker inspect -f '{{.State.Health.Status}}' "$db") == healthy ]] &&
     "${compose[@]}" exec -T relay node -e "fetch('http://127.0.0.1:5678/healthz/readiness').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))" >/dev/null 2>&1; then
    ready=true; break
  fi
  sleep 2
done
[[ $ready == true ]] || { echo 'Personal services unavailable' >&2; exit 1; }
for service in db relay; do
  id=$("${compose[@]}" ps -q "$service")
  [[ -n "$id" && $(docker inspect -f '{{.State.Running}}' "$id") == true ]]
done
"${compose[@]}" run --rm --no-deps --use-aliases -T operator --authorized-root /run/daily --revision "$rev" --host "$host"
