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

## Verified targeted WSL re-acceptance

**PASS — journey exit 0; stop exit 0.** One fresh run at approved revision
`7ec5d0b5fc969e9f4dc275b661b5c891453deacf` on
`development/stage1-confirmation-recheck`. The checkout was clean through runtime
and stopping. Only documentation changed afterward.

| Check | Result | Verified evidence |
| --- | --- | --- |
| Approved revision, daemon, local runtime and public kernel | PASS | Exact revision/daemon; accepted local application image; pinned host astronomy dependencies and public DE440s checksum. No dependency retrieval. |
| Original Stage 1 read-only inventory | PASS | Five stopped containers and four preserved volumes before and after; original container state unchanged. No original approval replay or original-state mount. |
| Separate project preflight | PASS | No recheck state, container, volume or network existed initially. |
| Focused confirmation tests | PASS | All three tests passed, including injected post-commit reply failures and independent ledger checks. Explicit changed-source checks passed. |
| Reviewed gateway overlay | PASS | Networkless overlay on the accepted local image; only the reviewed staging service module copied. No application-logic or migration modification. |
| Fresh synthetic initialization and startup | PASS | Separate database, native signed n8n relay, app, offline SDK gateway and worker started; signed status ready with zero initial backlog/quarantine. |
| Owner preview and foreign callback rejection | PASS | Preview/foreign callback caused no event/control/audit/slot/legacy-delivery write. |
| First owner confirmation | PASS | Relay classified approved reply; exactly one matching SDK reply; keyboard absent; independent committed-control match true. |
| Duplicate owner callback | PASS | Tested only after first confirmation passed; same successful reply, same committed control and unchanged counts. No idempotency mismatch. |
| Exactly-once persistence | PASS | One event, one control and one audit entry after both checks. |
| Zero delivery work | PASS | Zero notification slots, zero legacy delivery rows, zero slot attempts and zero persistent recorder attempts. |
| Recheck graceful stop | PASS | All five recheck containers stopped, each exit 0. Four recheck volumes and stopped containers preserved. |
| Original and unrelated resources | PASS | Original project state and unrelated running/all-container and volume inventories unchanged; accepted local base image unchanged. |
| First mismatch | PASS | None in this recheck. The original Stage 1 response failure was not reproduced or explained. |
| Timed reminders, runtime recovery, uncertainty and competing worker | NOT TESTED | Outside this single-silent-fixture recheck; prior Stage 1 missing acceptance remains pending. |
| Physical, Windows, real Telegram and production operations | NOT TESTED | No such actions; no host change, permanent installation, deployment or merge. |

Both first and duplicate diagnostics were identical:

```json
{"approved_replies":1,"audits":1,"controls":1,"deliveries":0,"events":1,"fallback_replies":0,"keyboard":"absent","matches_control":true,"relay":"approved_reply","replies":1,"slots":0}
```

Independent post-journey inspection returned events/controls/audits **1/1/1**,
slots/legacy deliveries/slot attempts **0/0/0**, and recorder attempts **0**.
No response body, review ticket, control/message identifier or credential was
published. No source correction or assertion relaxation was required. Preserve
both stopped projects. A successful fresh recheck does not retroactively turn
the original failed run into a pass, authorize reuse of its state, or complete
the outstanding broader Stage 1 acceptance.
