# First silent approval response investigation

PR #14 at db4a8c75 includes the original [Stage 1 result](LAPTOP_STAGE1_RESULTS.md). The external harness that stopped was outside Git. Its private response body was never logged. The preserved observation is one event, one control and one audit entry plus a failed single-reply assertion. It cannot distinguish an empty reply, fallback text, multiple messages, wrong control, residual keyboard or a harness interpretation error. The earlier networkless SDK reproduction with a successful stub returned the expected single reply. None of this establishes a change to the scheduling or authentication code.

The application takes the control ID from the JSON snapshot returned by lunar_api.approve_recurring and formats one English approval line ending in a period. The callback handler sends the reply through message.reply_text without a keyboard. The synthetic adapter records sendMessage text; answerCallbackQuery is an acknowledgement and contributes no chat message. The expected response is exactly one line matching the committed control UUID. A successful write and a successful owner-visible acknowledgement are separate acceptance conditions.

The correction is diagnostic. The staging gateway classifies the signed relay result before the SDK formats its response. The journey checks the final recorder output and the database independently, then prints only counts, fixed categories and an identity-match boolean. It stops on missing responses, fallback replies, malformed results and inconsistent state. The source scanner and eight staging tests passed in Work. The new SQLite tests reproduce post-commit confirmation failure with injected reply faults and exercise the positive checker. They do not reproduce the unknown original fault or exercise PostgreSQL idempotency. The fresh WSL regression runs the actual callback, relay and approval transaction and checks duplicate handling only after a fully acknowledged first decision.

## One WSL Codex task

Use a clean checkout of this stacked PR at the reviewed full revision. Run only the one silent synthetic fixture below. Check the independent daemon ID and the original stopped Stage 1 inventory read-only. Leave those containers, four volumes and original state directory untouched. The controller uses a separate fixed project, state directory, network and volume names when DINCHARYA_STAGE1_RECHECK is exactly 1. Stop on any existing resource with the new project name. Set PY, PG, N8N and KERNEL from the originally verified local Stage 1 inventory; no new runtime dependency or public image pull is needed. Set REV from the reviewed child PR head independently. Reuse the accepted application image and overlay only the reviewed staging gateway module. Run from the repository root in one shell.

```bash
set -euo pipefail
: "${REV:?}" "${PY:?}" "${PG:?}" "${N8N:?}" "${KERNEL:?}"
export DINCHARYA_STAGE1_RECHECK=1 PYTHONDONTWRITEBYTECODE=1
DAEMON=44c1ef83-c50e-4ecc-8f19-4b112bc40f29
old=sha256:fff0b1b58321339ad0de04804548cb8ff14c9a929e6eead08ce3cd96535493ca
test "$(git rev-parse HEAD)" = "$REV" && test -z "$(git status --porcelain)" || exit 1
test "$(docker info --format '{{.ID}}')" = "$DAEMON"
test "$(docker image inspect --format '{{.Id}}' "$old")" = "$old"
test ! -e "$HOME/.local/state/dincharya-stage1-recheck"
test -z "$(docker ps -aq --filter label=com.docker.compose.project=dincharya-stage1-recheck)"
test -z "$(docker volume ls -q --filter label=com.docker.compose.project=dincharya-stage1-recheck)"
test -z "$(docker network ls -q --filter name='^dincharya-stage1-recheck_default$')"
"$PY" -B -m unittest discover -s staging/laptop -p test_confirmation.py -v
ctx=$(mktemp -d)
git show "$REV:staging/laptop/service.py" >"$ctx/service.py"
# Tag only the verified local image under a fresh temporary name.
base_tag=dincharya-recheck-base:$(basename "$ctx" | tr '[:upper:]' '[:lower:]')
docker tag "$old" "$base_tag"
test "$(docker image inspect --format '{{.Id}}' "$base_tag")" = "$old"
printf 'ARG BASE\nFROM ${BASE}\nCOPY service.py /src/staging/laptop/service.py\n' >"$ctx/Dockerfile"
docker build --network none --pull=false --build-arg "BASE=$base_tag" --iidfile "$ctx/image-id" "$ctx"
pin=(--daemon "$DAEMON" --revision "$REV")
stage() { "$PY" -B staging/laptop/control.py "$1" "${pin[@]}" "${@:2}"; }
stage prepare --app "$(cat "$ctx/image-id")" --db "$PG" --relay "$N8N" --kernel "$KERNEL"
trap 'stage stop' EXIT
stage initialize
stage start
"$PY" -B staging/laptop/recheck.py "${pin[@]}"
```

The driver checks empty tables, owner preview and foreign callback denial. It submits one owner confirmation. A passing confirmation requires one event, one control, one audit, no slots or legacy deliveries, one matching approved reply, a successful relay classification and an absent keyboard. Only on this fresh fixture and only after this pass does it inject a duplicate owner callback and demand the same result. Any failure ends the run. Preserve both projects. Report the two exit codes (journey and stop), fixed diagnostic fields, initial/final project inventories and pass/fail only. Do not rerun an uncertain action, print response bodies or move to the timed reminder/Windows tests.
