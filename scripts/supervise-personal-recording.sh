#!/usr/bin/env bash
# Foreground supervision for a prepared synthetic fixture. No login task registration.
set -euo pipefail
[[ $# == 2 && $1 == --recorded-root && $2 == /* && -d $2 && ! -e $2/STOP ]]
root=$2
# Each invocation consumes a new pipe. Never rewind a transcript after an interruption.
[[ -p /dev/stdin ]]
python -m dincharya.personal_service --recorded --root "$root" <&0 &
child=$!
stop() { kill -TERM "$child" 2>/dev/null || true; }
trap stop TERM INT
trap 'stop; wait "$child" 2>/dev/null || true' EXIT
ready=false
for _ in {1..20}; do
  kill -0 "$child" || { wait "$child"; exit 1; }
  if python -m dincharya.personal_health --recorded-root "$root"; then ready=true; break; fi
  sleep 1
done
[[ $ready == true ]]
while kill -0 "$child" 2>/dev/null; do
  if [[ -e "$root/STOP" ]]; then stop; break; fi
  python -m dincharya.personal_health --recorded-root "$root" || exit 1
  sleep 5
done
wait "$child"
trap - EXIT
