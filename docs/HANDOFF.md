# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint — M2G Telegram application passes isolated acceptance

Clean entry at pushed `e2ca863b300b73f3ad96465800f9a1d4dc871d6a`; owner created
and agent verified `development/m2g-telegram-integration`. Git metadata remains
mounted read-only. This29-file checkpoint is uncommitted, no Git bypass/stage/
commit/push attempted. Previous M2F commit instructions are superseded.

- Owner authorized consolidated application implementation/testing, stopping
  before real Telegram messages. **G01–G04 passed, exit0** with actual SDK
  Update/CommandHandler/JobQueue, signed n8n orchestration, real psycopg role
  sessions, existing lunar/Gregorian APIs, process_batch and TelegramReminders.
  Only Telegram network IO is simulated; application has no Docker/psql shim.
- Birthday/anniversary fixture previews, separate explicit rule/occurrence
  approvals, rejection, reviewed cancellation and owner-only status implemented.
  SDK private owner identity, HMAC freshness/domain-separated keys, deterministic
  update/action IDs, review tokens and fresh SQL snapshots prevent forged/replay/
  stale authority. Body IDs never establish owner/DB authority.
- One polling owner and job; worker session lock covers claim/send/ack. Actual
  simulation produced exactly4 attempts (2 sent+receipts,1 definite failure then
  explicitly cancelled,1 uncertain). Repeat polling and two service-process/n8n
  restarts plus gateway SDK shutdown/rebuild preserve exact histories. Existing
  PostgreSQL container ID/start time and unrelated running-container set unchanged.
- Additive0009 owner identity/bounded delivery status only;0001–0008, worker,
  Gregorian model and astronomical fixtures unchanged. Actual worker denial of
  owner status API and Gregorian proposal/approval control passed.
- **73 focused offline tests pass**, no skips in the pinned /tmp SDK/driver venv.
  Sandbox asyncio IPC caused shutdown warnings; scoped permitted execution
  completed cleanly. Source/AST/JSON/SQL/link/diff/immutability checks pass.
  No old T00–T26, model/cadence/live suite rerun; no test weakened.
- Explicit real transport stays disabled by default. [Private acceptance runbook](M2G_TELEGRAM_ACCEPTANCE.md) and gated launcher prepare ONE dedicated test-bot
  fixture reminder, hidden local credentials, independent bot pin, required
  Telegram approvals, repeat-poll check and rollback/cleanup. Live flag/type,
  credential and SDK gates are tested; the real bot wire is NOT run or authorized.
- [Actual results](M2G_TELEGRAM_RESULTS.md), architecture/D24/roadmap/plan/readmes
  and GitHub issue2 updated. AGENTS unchanged. No production, private backup/2B
  search, deployment, other orchestrator or merge. Only the named schema accessed.

No unresolved synthetic application failure. Next is explicit owner authorization
for exactly one private fixture reminder with @dincharya_acceptance_test_bot,
fresh disposable DB and separately entered replacement credentials. Do not
schedule before explicit rule AND occurrence approval in Telegram. Astronomy,
production auth/source adoption, advance slots and broader operational/VPS gates
remain disabled/pending; this is not general calendar scheduling approval.

Normal WSL safe commands (29 explicit paths; review index before commit):

```bash
git branch --show-current
git status --short
git diff --check
git add -- \
  database/migrations/0009_lunar_delivery_status.sql \
  database/migrations/README.md \
  dincharya/lunar_service.py \
  dincharya/lunar_runtime.py \
  dincharya/lunar_http.py \
  telegram-gateway/gateway.py \
  telegram-gateway/reminder_handlers.py \
  telegram-gateway/lunar_handlers.py \
  telegram-gateway/lunar_acceptance.py \
  telegram-gateway/requirements-m2g.txt \
  telegram-gateway/README.md \
  workflows/m2g-lunar-acceptance.json \
  workflows/README.md \
  tests/integration/m2g_runner.py \
  tests/integration/m2g_server.py \
  tests/integration/m2g_bot.py \
  tests/integration/m2g_relay.py \
  tests/integration/m2g_live_prepare.py \
  tests/integration/m2g_live_server.py \
  tests/integration/e2e_bridge.js \
  tests/integration/README.md \
  tests/test_lunar_application.py \
  docs/M2G_TELEGRAM_RESULTS.md \
  docs/M2G_TELEGRAM_ACCEPTANCE.md \
  docs/HANDOFF.md \
  docs/ARCHITECTURE.md \
  docs/DECISIONS.md \
  docs/MILESTONE2_PLAN.md \
  docs/ROADMAP.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "feat: integrate authenticated Telegram lunar acceptance"
git push -u origin development/m2g-telegram-integration
```

## Prior integration evidence (historical)

- Last full offline suite: **196 tests passed**. Final focused checkpoint: four
  migration-renderer tests and six reminder-worker tests passed; application
  runner, migration renderer and worker Python AST checks passed.
- **2C passed**, including final runner revision: verified pinned local Linux
  Docker Desktop identity; three healthy services; exact runtime isolation;
  synthetic application initialization; owner/bootstrap; non-Code imports;
  manual synthetic-pass; at least five successful scheduled outputs; n8n-only
  restart with PostgreSQL unchanged; at least three successful outputs started
  after restart readiness; no duplicate observed cadence slots; persistent durable
  job/occurrence identities and non-regressing clocks; retained legacy arrays.
- **2D/2E initial database integration passed** on the exact operator-authorized
  PostgreSQL schema: unchanged baseline bytes loaded into dincharya_app_test;
  both checksummed migrations applied; repeat migration application was a no-op;
  gregorian.sql and reminders.sql assertions passed. Baseline was not copied into
  Git and is not a production migration. Existing baseline functions are not
  collectively certified by these tests.
- Both successful runs verified teardown of test containers/network and unchanged
  original running container IDs. No production resources/data, real bot, Code
  workflow, production scheduler state or credentials were used.
- The last request to run expanded application checks was interrupted before any
  execution result/session was returned. Do not claim that rerun passed or started.
  No Docker was run during the final usage-preservation checkpoint.

## Runtime findings and scope

The exact image is n8n 2.47.3 with nodes-base 2.47.2. Default durable scheduling
intercepts Schedule Trigger rules and uses scheduled_job/scheduled_task state.
Legacy recurrenceRules/recurrenceRuleSignatures are preserved, but successful
retention does not prove they control the default runtime or historical engines.
The synthetic seven-minute rule is provisioned as a durable 420-second interval;
its full interval was not waited out. Fast emissions/restart were tested directly.

The create API drops supplied staticData (confirmed in API and test DB). Native
CLI import preserves it. CLI operations need a separate internal task-broker port
5680 beside server port 5679. Test n8n needs a bounded UID-1000 cache tmpfs; its
root filesystem remains read-only. API sessions are reused in private tmpfs to
avoid login rate limits and refreshed after restart when necessary.

Use only tests/integration/compose.json, project dincharya-m2c-synthetic,
--env-file /dev/null and integration profile. The runner pins local image IDs,
uses empty temporary Docker config/HOME and a fixed local socket, rejects remote
context/host overrides, and verifies the separately pinned daemon ID. Existing
test resources cause refusal. No published ports, persistent volumes, production
mounts or privileged containers. Cleanup is project-specific; forced termination
or daemon failure can still leave disposable resources.

## Implementation and unverified additions

- 0001_gregorian_occurrences.sql: strict proposal validation, daily/ISO-week/month/
  year matching, inclusive until dates, skipped invalid calendar dates, stable
  occurrence-date overrides/cancellations, series changes, stale proposal snapshots,
  authorized/idempotent decisions and explicit conflict override. Conflict review
  defaults to 730 days and is bounded to 3660; it is not proof of no conflicts for
  an infinite series. Overnight events remain unsupported.
- 0002_occurrence_reminders.sql: retain legacy ledger rows and event/date identity;
  materialize due work; claims/worker tokens/leases; definitive rejection retries
  with bounded backoff and five-attempt cap; uncertain outcomes/expired leases
  quarantined without automatic resend; bounded outage lookback (default six hours);
  preserve sent history; guard edits while a send is in flight.
- dincharya/reminders.py is an adapter-injected single-batch worker, tested offline.
  It opens no connections and performs no real Telegram I/O itself. Database and
  transport adapters and one-time gateway wiring now passed isolated acceptance.
  Operator resolution of uncertain sends and deployment remain future work.
  A batch abort can leave
  remaining claims to expire into quarantine; external exactly-once is not claimed.
- Parallel duplicate decisions, competing reminder claims and concurrent
  acknowledgement now passed multi-session acceptance. Checksum-corruption
  rejection remains source-reviewed/syntax-checked only; it was not rerun here.
- Five-attempt exhaustion and one-time gateway transport wiring now passed. Broad
  outage/recovery permutations, adversarial API cases, legacy API interaction and
  uncertain-send reconciliation still need coverage before closing all of 2D/2E.

## Source/provenance boundaries

Only the exact application-schema.sql path authorized in the conversation was
opened, read-only. No backup directory, n8n.dump, credential table or other backup
artifact was scanned. The three named repository docs identify **no exact original
review/provenance manifest path**. Manifest location remains missing; do not guess
or search private directories. The user's source authorization does not certify
all schema functions or authorize production application/source promotion.

Historical foundation checkpoint was `ceeba98`; the foundation commit
`b80a91d8` subsequently landed on main. 2C is complete for its synthetic scope.
2D and 2E remain partially complete.

Historical 2B evidence remains: four
current workflows, 94 history versions, two structural candidates; current and
published bodies remain separate; seven Code bodies were neither executed nor
cleared. No complete production workflow/schema baseline has been adopted in Git.

