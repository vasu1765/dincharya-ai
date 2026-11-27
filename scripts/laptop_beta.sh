#!/usr/bin/env bash
# Fresh disposable resources only. Staging leaves STOP present and no bot key.
set +x
set -euo pipefail
umask 077
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.
action=${1:?stage|check|start|stop|cleanup}
state=${2:?absolute fresh private staging directory}
: "${REV:?exact reviewed commit required}"
[[ $state = /* && $state != *,* && $state != *:* && $(git rev-parse HEAD) == "$REV" && -z $(git status --porcelain) ]]
daemon=$(docker info --format '{{.ID}}')
[[ $daemon == 44c1ef83-c50e-4ecc-8f19-4b112bc40f29 ]]
read -r pg_image app_image relay_image < <(python3 -B -c 'from dincharya.attended_runtime import PG,APP,N8N;print(PG,APP,N8N)')
session=$state/session
if [[ $action == stage ]]; then
  mkdir -m 700 -- "$state"
  mkdir -m 700 "$session" "$state/source" "$state/setup"
  openssl rand -hex 12 > "$state/tag"
  printf '%s' "$REV" > "$state/revision"
fi
[[ -O $state && ! -L $state && $(stat -c %a "$state") == 700 && $(cat "$state/revision") == "$REV" ]]
tag=$(cat "$state/tag")
[[ $tag =~ ^[0-9a-f]{24}$ ]]
label="org.dincharya.laptop-beta=$tag"
prefix="dincharya-lb-$tag"
sql() { docker exec -i "$pg" psql -XqAt -v ON_ERROR_STOP=1 -U postgres -d dincharya_attended_test "$@"; }
owned() {
  [[ $(docker inspect --format '{{index .Config.Labels "org.dincharya.laptop-beta"}}' "$1") == "$tag" ]]
}
preflight() {
  python3 -B scripts/attended_operator_host.py --profile laptop-beta "$session/manifest.json" "$1" "$pg" "$app" "$relay"
}
if [[ $action == stage ]]; then
  [[ $(id -u) -gt 0 ]]
  for img in "$pg_image" "$app_image" "$relay_image"; do
    [[ $(docker image inspect --format '{{.Id}}' "$img") == "$img" ]]
  done
  : "${KERNEL:?reviewed public de440s.bsp}" "${CERTIFI_WHEEL:?reviewed astronomy wheel}"
  wheel=certifi-2025.10.5-py3-none-any.whl
  cp -- "$KERNEL" "$session/de440s.bsp"
  cp -- "$CERTIFI_WHEEL" "$session/$wheel"
  python3 -B - "$session" <<'PY'
from pathlib import Path
import hashlib,sys
from dincharya.attended_runtime import KERNEL_SHA,WHEEL,verify_wheel
p=Path(sys.argv[1])
verify_wheel(p/WHEEL)
if hashlib.sha256((p/'de440s.bsp').read_bytes()).hexdigest()!=KERNEL_SHA: raise ValueError("kernel")
PY
  git archive "$REV" -- dincharya prototypes/panchang | tar -x -C "$state/source"
  git archive "$REV" -- dincharya prototypes/panchang tests/integration/beta_relay_journey.py workflows/m2g-lunar-acceptance.json | tar -x -C "$state/setup"
  cp "$state/revision" "$session/revision"
  touch "$session/STOP"
  for role in poller worker relay; do openssl rand -hex 32 > "$session/$role.key"; done
  docker network create --internal --label "$label" "$prefix-private" > "$state/private"
  docker network create --label "$label" "$prefix-out" > "$state/out"
  private=$(cat "$state/private")
  POSTGRES_PASSWORD=$(openssl rand -hex 32)
  export POSTGRES_PASSWORD
  docker run --label "$label" --pull never -d --network "$private" --network-alias db --tmpfs /var/lib/postgresql/data -e POSTGRES_PASSWORD -e POSTGRES_DB=dincharya_attended_test "$pg_image" > "$state/pg"
  unset POSTGRES_PASSWORD
  pg=$(cat "$state/pg")
  ready=false
  for i in {1..60}; do
    if [[ $(docker exec "$pg" cat /proc/1/comm) == postgres ]] && sql -c 'SELECT 1' >/dev/null 2>&1; then ready=true; break; fi
    sleep 1
  done
  [[ $ready == true ]]
  sql -f - < database/attended/0001_disposable.sql
  sql -f - < database/attended/0002_operator.sql
  for role in poller worker; do
    printf "ALTER ROLE attended_%s LOGIN PASSWORD '%s';\n" "$role" "$(cat "$session/$role.key")" | sql -f -
  done
  docker run --label "$label" --pull never -d --network "$private" --network-alias relay --tmpfs /home/node/.n8n:uid=1000,gid=1000 -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_SECURE_COOKIE=false -e EXECUTIONS_DATA_SAVE_ON_SUCCESS=none -e EXECUTIONS_DATA_SAVE_ON_ERROR=none "$relay_image" > "$state/relay"
  relay=$(cat "$state/relay")
  docker run --rm --label "$label" --pull never --network "$private" --user "$(id -u):$(id -g)" -v "$state/setup:/setup:ro" -w /setup -e PYTHONPATH=/setup:/setup/tests/integration --entrypoint python "$app_image" -B -c 'from beta_relay_journey import install;install(print)'
  docker run --label "$label" --pull never -d --network "$private" --network-alias app --hostname "$daemon" --user "$(id -u):$(id -g)" --read-only --cap-drop ALL --security-opt no-new-privileges -v "$state/source:/candidate:ro" -v "$session:/run/attended:ro" -w /candidate -e PYTHONPATH=/candidate --entrypoint sleep "$app_image" infinity > "$state/app"
  app=$(cat "$state/app")
  docker network connect "$(cat "$state/out")" "$app"
  python3 -B - "$session" "$REV" "$daemon" <<'PY'
import json,sys,time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from dincharya.attended_runtime import PG,APP,N8N,KERNEL_SHA
now=int(time.time())
def event(title,delay):
    return 'Schedule '+title+' on '+datetime.fromtimestamp(now+delay,ZoneInfo('Asia/Kolkata')).strftime('%Y-%m-%d at %H:%M')
m=dict(profile='laptop-beta',sha=sys.argv[2],host=sys.argv[3],pg=PG,app=APP,n8n=N8N,owner=93001,bot=93002,
       bot_username='StagingFixtureBot',start=now,end=now+1800,silent=event('Silent',600),reminder=event('Reminder',900),
       question='What was the tithi on 2023-12-06?',kernel_sha256=KERNEL_SHA)
(Path(sys.argv[1])/'manifest.json').write_text(json.dumps(m))
PY
  preflight "$(sha256sum "$session/manifest.json" | cut -d' ' -f1)"
  [[ -f $session/STOP && ! -e $session/bot.key && $(sql -c 'SELECT count(*) FROM attended.operator_approval') == 0 && $(sql -c 'SELECT count(*) FROM attended.attempt') == 0 ]]
  docker exec -i "$app" python -B - <<'PYTHON'
import secrets
import time
import httpx
from dincharya.attended_operator import signed_route
from dincharya.attended_runtime import telegram_tls
from dincharya.lunar_service import sign
_,digest=telegram_tls()
key=secrets.token_hex(32)
with httpx.Client(timeout=4,trust_env=False,follow_redirects=False) as client, signed_route(key,client) as route:
    for n in range(20):
        reply=client.post("http://relay:5678/webhook/m2g-lunar",json={},headers={"x-dincharya-signature":"invalid"})
        if reply.status_code==404 and n<19:
            time.sleep(.25)
            continue
        if reply.status_code not in (200,403) or reply.json()!={"status":"denied"}:
            raise ValueError("Unarmed relay denial mismatch")
        break
    value={"purpose":"unarmed-staging","nonce":secrets.token_hex(16)}
    route(value,sign(key,"command",value))
print("PASS signed unarmed relay and verified CA sha256="+digest)
PYTHON
  echo 'PASS parked laptop runtime; zero approvals and zero attempts'
  exit
fi
if [[ $action == cleanup ]]; then
  [[ ${CLEANUP_TAG:-} == "$tag" && -f $session/STOP ]]
  # Remove only objects bearing this run's cryptographically random label, including partial stages.
  ids=$(docker ps -aq --filter "label=$label")
  for id in $ids; do owned "$id"; docker rm -fv "$id"; done
  nets=$(docker network ls -q --filter "label=$label")
  for id in $nets; do docker network rm "$id"; done
  [[ -z $(docker ps -aq --filter "label=$label") && -z $(docker network ls -q --filter "label=$label") ]]
  echo 'Disposable resources removed; private host files retained for owner-reviewed disposal.'
  exit
fi
pg=$(cat "$state/pg"); relay=$(cat "$state/relay"); app=$(cat "$state/app")
for id in "$pg" "$relay" "$app"; do owned "$id"; done
if [[ $action == stop ]]; then
  touch "$session/STOP"
  docker stop -t 3 "$app" >/dev/null
  sql -c 'UPDATE attended.session SET enabled=false'
  exit
fi
: "${APPROVAL_DIGEST:?exact manifest SHA-256}"
preflight "$APPROVAL_DIGEST"
if [[ $action == check ]]; then exit; fi
[[ $action == start && ${LIVE_SESSION_APPROVAL:-} == "$APPROVAL_DIGEST" && -f $session/STOP && -s $session/bot.key ]]
# Never arm on the synthetic identity and never replace a consumed approval.
python3 -B - "$session/manifest.json" "$APPROVAL_DIGEST" "$REV" "$daemon" <<'PY' | sql -f -
import sys,time
from pathlib import Path
from dincharya.attended_operator import Approval
a=Approval.load(Path(sys.argv[1]).read_bytes(),*sys.argv[2:])
if a.profile!='laptop-beta' or a.bot==93002 or a.owner==93001 or not a.start<=time.time()<a.end: raise ValueError('unapproved window or fixture')
print(f"BEGIN; INSERT INTO attended.session VALUES(true,{a.owner},{a.bot},to_timestamp({a.start}),to_timestamp({a.end}),true); INSERT INTO attended.operator_approval(singleton,digest) VALUES(true,'{sys.argv[2]}'); COMMIT;")
PY
rm "$session/STOP"
trap 'touch "$session/STOP"; sql -c "UPDATE attended.session SET enabled=false" >/dev/null' EXIT
docker exec "$app" python -B -m dincharya.attended_operator --attended --profile laptop-beta --approval "$APPROVAL_DIGEST"
