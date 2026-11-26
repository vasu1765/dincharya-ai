#!/usr/bin/env bash
# Approved Linux mount only. Refuse an unmounted fallback directory.
set -euo pipefail
umask 077
id=${1:?full database container ID}
mount=${2:?mounted off-device filesystem}
source_pin=${3:?owner-approved findmnt SOURCE}
cert=${4:?recipient PEM}
pin=${5:?approved PEM SHA256}
[[ "$id" =~ ^[0-9a-f]{64}$ && "$mount" == /* && $(realpath -- "$mount") == "$mount" ]]
[[ $(findmnt -n -M "$mount" -o SOURCE) == "$source_pin" ]]
[[ $(docker inspect -f '{{.Image}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "com.docker.compose.service"}}' "$id") == 'sha256:ff87138949ad9a46f32ff23bd6852b52ce024a13dffe9b4087be98292cdd3b4f dincharya-personal db' ]]
dest="$mount/dincharya-encrypted"
[[ -d "$dest" && ! -L "$dest" ]]
# Fail closed rather than placing a plaintext database dump in the default /tmp.
[[ $(findmnt -n -M /dev/shm -o FSTYPE) == tmpfs ]]
tmp=$(mktemp -d /dev/shm/dincharya-daily.XXXXXXXX)
trap 'rm -rf -- "$tmp"' EXIT
docker exec "$id" pg_dump -U personal_backup -Fc dincharya_personal_candidate > "$tmp/dump"
docker exec -i "$id" pg_restore -l < "$tmp/dump" >/dev/null
PYTHONPATH=. python3 -B -m dincharya.beta_archive "$dest" "$cert" "$pin" < "$tmp/dump"
