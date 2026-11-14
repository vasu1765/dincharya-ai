# M2G Telegram integration — isolated application acceptance passed

## Owner-authorized private Telegram acceptance — PASSED, 2026-11-14

Pushed application checkpoint `6848d4f2b7a1bbbb6d61c0bbf162bf6f05bebd4d`
verified on development/m2g-telegram-integration; entry tree clean. Owner explicitly
approved ONE real reminder to the owner's private chat using
@dincharya_acceptance_test_bot, one synthetic birthday fixture and fresh disposable
PostgreSQL/n8n. The committed application and documented launcher were reused;
no integration rebuild, code fix or successful synthetic suite rerun.

| Acceptance check | Actual sanitized evidence |
| --- | --- |
| Credentials | Entered with hidden normal-WSL terminal input. Named file regular/non-symlink, correct owner, single hardlink, mode600 and parent700 verified. No token/owner/bot numeric IDs or file contents printed, logged or committed. |
| Preflight | Exact daemon44c1ef83-c50e-4ecc-8f19-4b112bc40f29, pinned images, fresh three-service standalone project and runtime isolation verified. Only named authorized schema baseline loaded and validated; no other backup/source accessed. |
| Bot and DB identity | Existing real application startup verified the independently pinned dedicated bot identity and scoped database owner. Gateway started in explicit lunar live-acceptance mode with a restricted runtime configuration. |
| Explicit approvals | Owner confirmed BOTH rule and occurrence approvals in Telegram. Read-only observation: one series, approved rule, approved occurrence/projection and queued delivery; zero attempts before its approved due time. |
| Delivery/acknowledgement | Exactly one real attempt; one sent delivery and one acknowledged paired receipt. No failed, sending or uncertain record remained. No IDs or payloads exported. |
| Owner observation | Owner explicitly confirmed “Exactly one reminder received” for Reminder: Synthetic lunar fixture: success, excluding preview/approval/status replies. |
| Duplicate prevention | Initial acknowledged observation08:55:14 Asia/Kolkata; further observation08:56:31 showed the same one delivery/attempt/receipt after more than two additional15-second polling intervals (at least77 seconds). No second request, replan, resend or reset. |
| Graceful stop | Gateway exited0 after Ctrl-C before STOP was sent to the launcher. |
| Final verification/cleanup | Launcher required exactly one sent+receipt/attempts1 delivery and one series, exited0, removed disposable project/network and verified original unrelated running-container IDs unchanged. |

Condensed actual launcher output:

```text
Starting pinned disposable synthetic stack
Three healthy services; runtime isolation verified
PASS G01 real psycopg/scoped roles, signed n8n orchestration and application HTTP service
Sanitized delivery summary: [{"state":"sent","attempts":1,"has_receipt":true}]
PASS one acknowledged live reminder; owner must separately confirm exactly one received message
Removing only the disposable integration project
Teardown verified; original running container IDs unchanged
exit status 0
```

The separate exactly-one owner confirmation was received before shutdown. The
approved20-minute fixture time was retained; monitoring used read-only transactions
and sanitized aggregate counts only. The temporary gateway configuration and
socket/role environments were removed through normal launcher cleanup; the owner's
original credentials file remains restricted outside Git and is not an artifact.

No live failure, blind retry, history reset, delivery rescheduling or manual SQL
approval occurred. No production credential/database/service access, deployment,
main merge or astronomical scheduling. This completes the specific one-reminder
private acceptance authorization; it does NOT authorize another real send/run.
Earlier “live not authorized/executed” statements below are historical to the
preceding synthetic implementation checkpoint and superseded only for this run.
Broader calendar/source/operational/VPS gates remain unchanged.

## Outcome and boundaries

Clean entry at pushed `e2ca863b300b73f3ad96465800f9a1d4dc871d6a` on
`development/m2f-synthetic-e2e`; owner created and agent verified
`development/m2g-telegram-integration`. Git metadata remains read-only; new source
is uncommitted. Exact consolidated commit commands are in HANDOFF. No Git bypass.
No open PR exists for this branch yet.

**G01–G04 passed with the real SDK handlers, psycopg, n8n and existing worker.**
Telegram network IO was simulated.73 focused unit/security/regression checks pass.
Final disposable teardown and unchanged unrelated running-container IDs passed.
No real Telegram call/message, production access, deployment or main merge.
Astronomical scheduling remains disabled; only explicit synthetic fixtures work.
This completes the requested integration checkpoint, not all operational/VPS or
calendar-adoption acceptance.

## Application implementation

- [lunar_handlers](../telegram-gateway/lunar_handlers.py) registers real SDK commands
  for birthday/anniversary fixture requests, separate rule/occurrence approvals,
  rejection, reviewed cancellation and owner-scoped status. SDK effective_user and
  private effective_chat must match the configured owner. Bot/foreign/group/edited
  updates reject before HTTP/database work. No message-body actor IDs are accepted.
- [gateway](../telegram-gateway/gateway.py) adds only the explicit gated
  --lunar-acceptance CONFIG --live-approved mode. Existing normal/Gregorian modes
  remain. Either registration claims a single bot_data polling owner; duplicate
  registrations reject. One SDK job (max_instances1) orchestrates ticks through
  n8n; no second scheduler/worker implementation.
- [lunar_service](../dincharya/lunar_service.py) authenticates canonical HMAC
  envelopes across n8n, separate command/tick/review keys,60-second request freshness
  and domain separation. Telegram update ID derives deterministic action/series
  UUIDs. Replayed requests/decisions use existing SQL idempotency, not new IDs.
  Server-signed30-minute review tokens bind request, stage and fingerprint; the
  existing SQL API rejects stale state. Client approval flags/user IDs are not
  database authority. Unknown actor fields reject.
- [lunar_runtime](../dincharya/lunar_runtime.py) makes explicit real psycopg
  connections with pinned database/login, no inherited PG settings, no implicit
  password/service files, statement timeout, fixed timezone/date style and
  superuser/role-escape rejection. Owner/calculator/worker logins are distinct.
  The trusted DB owner must match configured Telegram ownership. Application code
  has no Docker, psql, SQL literal bridge or test-module dependency.
- [HTTP endpoint](../dincharya/lunar_http.py) bounds requests and authenticates
  before operations; Unix sockets have mode600 inside private directories. A
  repository-owned [native workflow](../workflows/m2g-lunar-acceptance.json) forwards
  the signed command and header, with no Code node or new schedule trigger. The
  template is inactive and not imported into existing services.
- Existing SyntheticLunarPostgres, Gregorian once projection, PostgresReminders,
  process_batch, SQL leases/retries/receipt acknowledgement and TelegramReminders
  are reused. Worker session lock(20261112,3) covers claim/send/ack across processes.
  Sent/uncertain history is never reset or resent. Definite failure alone uses
  existing retry/backoff. Ambiguous storage replies recommend inspecting existing
  status, not creating another reminder.
- Additive [0009](../database/migrations/0009_lunar_delivery_status.sql) exposes only
  authenticated owner identity and bounded delivery metadata (latest20 records,
  state/attempt/due/receipt-presence). No payload, chat/message IDs or lease tokens.
  No new event/queue/history tables or change to0001–0008. Only owner role can call;
  worker permission denial was tested against actual PostgreSQL.

The real TelegramReminders transport already validates destination/message
acknowledgements and quarantines unknown/429 outcomes. New runtime construction
keeps real delivery disabled by default, requires explicit live approval plus
restricted configuration and independently verifies the dedicated test bot.
Only the live SDK mode calls run_polling; no real polling was run in development.
SDK/HTTP diagnostics are suppressed/token-redacted in that mode. The future
[private acceptance procedure](M2G_TELEGRAM_ACCEPTANCE.md) includes one-reminder
scope, secure local credential entry, explicit approvals, status/duplicate checks
and rollback/cleanup. It has not been executed live.

## Actual isolated runtime

Command executed with scoped sandbox permission:

```bash
PYTHONDONTWRITEBYTECODE=1 /tmp/dincharya-m2g-runtime/bin/python -B \
  tests/integration/m2g_runner.py \
  --baseline /home/vasu1765/dincharya-backups/baseline-20261112T132918Z-d5V7Hf/application-schema.sql \
  --expected-daemon-id 44c1ef83-c50e-4ecc-8f19-4b112bc40f29 \
  --execute-approved
```

Uses the existing standalone2C compose/project, --env-file /dev/null and exact
pinned PostgreSQL17/n8n2.47.3 images; no host ports/new container service/image.
Daemon pin checked before creation, fresh application DB, SCRAM TCP/container-local
socket trust, read-only roots, exact mounts and internal network verified. Only
one authorized schema file read and validated unchanged. All9 migrations installed.
Statement/error/parameter logging suppressed before generated credentials.

Test-only opaque byte relays let real psycopg/httpx connect across isolated Unix
sockets without published ports. Reverse HTTP relay forwards bytes/auth headers,
not application decisions. They live under tests/integration and are not imported
by application modules. The SDK uses BaseRequest simulation only for Telegram IO;
all SDK Update parsing, CommandHandler callbacks and JobQueue operation are real.
The existing TelegramReminders processes simulated HTTP200/400/500 responses, with
an append-every-attempt PostgreSQL journal. No simulator dedupe hides duplicate sends.

| Gate | Observed pass |
| --- | --- |
| G01 | Real scoped psycopg sessions/identity guards, signed n8n route, new application service process, migration0009. |
| G02 | Real SDK foreign/group/bot/edited denials; birthday and wedding-anniversary synthetic previews; separate approvals; same-update replay idempotency; stale/reject/cancel; forged HTTP body denied. |
| G03 | Exactly one automatic gateway polling job; existing worker; success+anniversary sent with paired receipts/attempts1; definite failure failed, accepted-but-response-lost uncertain; exactly4 simulated attempts total. Failed work explicitly cancelled preserving attempts. |
| G04 | Two service OS-process/n8n restarts and gateway SDK shutdown/rebuild cycles; PostgreSQL ID/start time unchanged; repeated polling creates no send; exact history unchanged; worker denied owner API; native Gregorian proposal/approval control passed. |
| Teardown | Service stopped, relays closed, disposable project/network removed, original unrelated running-container IDs unchanged, exit0. |

Condensed final output:

```text
Starting pinned disposable synthetic stack
Three healthy services; runtime isolation verified
PASS G01 real psycopg/scoped roles, signed n8n orchestration and application HTTP service
PASS G02 actual SDK authorization, birthday/anniversary previews, separate approvals, replay/stale/reject/cancel
PASS G03 automatic single gateway polling -> existing worker -> real Telegram adapter/simulated HTTP -> receipts/quarantine
PASS G04 real process/n8n/gateway restart, exact history, permissions and Gregorian control
Removing only the disposable integration project
Teardown verified; original running container IDs unchanged
exit status 0
```

Accelerated1-second test polling emitted expected max_instances1 skip warnings
while an earlier tick ran; no additional job or send was created. Actual live
configuration uses the established15-second cadence. The immutable journal had
exactly4 entries: two accepted sent outcomes, one definite failure and one accepted
uncertain outcome. Rejected/stale/cancelled requests never produced delivery.

The stale case advances only a synthetic observation counter under the scheduler
mutex; it does not reset delivery state or fabricate live astronomical evidence.
No old T00–T26, cadence, calendar-model or live acceptance suite was repeated.
Application success required no authorization/history/isolation check relaxation.
After the runtime pass, only equivalent fixture configuration hooks and guarded
future-live code, input hardening and safer error wording were added; SQL/worker
transitions and runtime assertions are unchanged. Those additions passed offline
checks; the actual live wire remains untested and unauthorized.

## Offline verification and dependencies

Python3.12.3; isolated /tmp venv, public PyPI with --isolated/--no-cache-dir after
network permission. Existing production/global Python was not modified. Exact
verified versions are [requirements-m2g.txt](../telegram-gateway/requirements-m2g.txt).
No real bot token or existing credential file was read or requested.

```bash
/tmp/dincharya-m2g-runtime/bin/python -B -m unittest \
  tests.test_lunar_application tests.test_reminder_gateway_preflight \
  tests.test_reminder_worker tests.test_reminder_adapters \
  tests.test_synthetic_e2e tests.test_migrations \
  tests.test_focused_application_runner tests.test_lunar_postgres -q
```

73 tests passed, no skips in that environment. Covers SDK authentication/command
routing, stage/token tamper/expiry, body authority refusal, disabled live gates,
private file restrictions, real-transport authorization, inherited-PG rejection,
no duplicate polling registration, migration packaging, relevant existing worker/
Gregorian adapter/receipt/retry/429/finish-failure and bridge regressions. Initial
sandbox asyncio executor shutdown hit IPC restrictions (assertions passed with
shutdown warnings); narrowly permitted execution outside sandbox completed cleanly.
No check was weakened to hide that environment limitation.

Static AST/JSON/SQL framing, Markdown links/fences, explicit source-safety and diff
checks pass. Existing0001–0008, original astronomical evidence, Gregorian SQL and
worker/transport bodies remain unchanged.0009 SHA-256:
`273a9611c584d6d43764d6a993a1df12bde528dc982534cb43c766e8754fde6d`.

## Remaining approval and limitations

The requested application workflow passes isolated testing; no unresolved synthetic
failure remains. **Explicit owner authorization for one private dedicated test-bot
acceptance is the next gate**, not another design-only milestone. The prepared
launcher rejects missing flags before opening credentials or starting resources,
then enables only one fixture type, validates the bot, exports a restricted minimal
gateway config and requires exactly one sent+acknowledged delivery at completion.
Both live flags, secure replacement credentials and explicit Telegram rule and
occurrence approvals are required. No scheduling precedes occurrence approval.

Real bot/network behavior, token validity and owner exactly-one receipt confirmation
cannot be claimed before that live run. There is no production deployment/auth/ACL
adoption, VPS supervision/restore acceptance, general lunar engine/festival/advance
slot enablement or other orchestrator. Those broader Milestone2 gates remain.
