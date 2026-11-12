#!/usr/bin/env bash
# ADMINISTRATOR ONLY. Do not execute from Codex. No live-container operations.
set +x
set -Eeuo pipefail
umask 077
exec 4>&2
for tool in docker python3 mktemp sha256sum id; do
  command -v "$tool" >/dev/null 2>&1 || { printf 'Missing source-export dependency.\n' >&4; exit 1; }
done
[[ -n "${SCHEDULER_SOURCE_ROOT:-}" ]] || { printf 'Set SCHEDULER_SOURCE_ROOT to an existing owned mode-700 directory outside Git.\n' >&4; exit 1; }
# No credential/configuration files are read by preflight.
python3 -B - "$SCHEDULER_SOURCE_ROOT" <<'PY'
import os, stat, sys
from pathlib import Path
root=Path(sys.argv[1])
if not root.is_absolute() or any(p.is_symlink() for p in (root,*root.parents)):
    sys.exit('Unsafe private root.')
s=root.stat()
if s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) != 0o700:
    sys.exit('Private root must be owned by this user with mode 700.')
for p in (root,*root.parents):
    if (p/'.git').is_file() or (p/'.git/HEAD').is_file() or ((p/'HEAD').is_file() and (p/'objects').is_dir()):
        sys.exit('Source output must stay outside Git.')
PY
source_output="$(mktemp -d "$SCHEDULER_SOURCE_ROOT/n8n-scheduler-2.47.3-XXXXXX")"
exec 2>"$source_output/export.private.log"
trap 'printf "Source export failed; inspect private log. No n8n workflow was started.\n" >&4' ERR
set -C
image_id="$(docker image inspect --format '{{.Id}}' 6723b440354b)"
[[ "$image_id" =~ ^sha256:6723b440354b[0-9a-f]{52}$ ]]
printf '%s\n' "$image_id" > "$source_output/image-id.private.txt"
# Start only a disposable, offline, read-only source-copy container. Override n8n
# entrypoint; no live volumes, credentials, env files or Docker socket mounts.
docker run --rm --pull=never --network=none --read-only --cap-drop=ALL \
  --security-opt=no-new-privileges --user "$(id -u):$(id -g)" \
  --entrypoint /bin/sh "$image_id" -ec '
    root=/usr/local/lib/node_modules/n8n
    test "$(node -p "require(\"$root/package.json\").version")" = 2.47.3
    cd "$root"
    test -f node_modules/n8n-nodes-base/dist/nodes/Schedule/ScheduleTrigger.node.js
    test -f node_modules/n8n-nodes-base/package.json
    tar -chf - package.json node_modules/n8n-nodes-base/package.json \
      node_modules/n8n-nodes-base/dist/nodes/Schedule
  ' > "$source_output/scheduler-source.tar.partial"
test -s "$source_output/scheduler-source.tar.partial"
python3 -B - "$source_output" <<'PY'
import os, sys
from pathlib import Path
root=Path(sys.argv[1])
os.link(root/'scheduler-source.tar.partial',root/'scheduler-source.tar')
os.unlink(root/'scheduler-source.tar.partial')
PY
printf '%s\n' '2.47.3 (package metadata checked inside the pinned local image)' > "$source_output/verified-version.private.txt"
(
  cd -- "$source_output"
  sha256sum scheduler-source.tar image-id.private.txt verified-version.private.txt > SHA256SUMS
)
printf '%s\n' 'STATIC_SOURCE_EXPORTED: package metadata and bounded Schedule source subtree only.' > "$source_output/EXPORTED"
printf 'Private scheduler source exported: %s\n' "$source_output"
