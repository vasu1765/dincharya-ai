# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint

Branch `development/m2-recovery-acceptance`, pushed base `db87193` (D10 and prior
recovery checkpoint). Current local task completes the requested 2D adversarial
API matrix and adds nullable Telegram receipt persistence. [Issue #2](https://github.com/vasu1765/dincharya-ai/issues/2)
tracks ALL Milestone 2, including Hindu Panchang and operational acceptance before
other domains/orchestrators. PR #1 remains merged; no deployment or main merge here.

Migration 0004 adds paired nullable chat/message IDs and unique receipt identity.
The new acknowledgement function delegates the unchanged old token/lease check,
then stores receipt in the same transaction as sent state. Historical IDs stay
NULL; old workers retain the four-argument API. New typed transport receipts must
match destination and have a usable message ID. Worker/commit failure never
replays the HTTP call. Gateway preflight requires all four migrations/API before
registering ticks. Migrations 0001–0003 and original baseline bytes are unchanged.

New adversarial SQL passed invalid action/scope/identity, malformed/non-Gregorian
rules, requester/force/horizon/decision checks and event/rule/override snapshot
staleness. Multi-session conflict, stale update, approve/reject and authorization
races passed. Receipt upgrade/history, wrong/expired token, invalid pair/outcome,
atomic failure rollback, replay/uniqueness and competing acknowledgements passed.
35 unique focused unit/preflight tests passed across scoped runs (26 reminder/
config checks, 2 optional gateway-dependency checks, 4 renderer and 3 runner tests).
No full suite result is claimed. See [sanitized results](M2_RECEIPTS_ADVERSARIAL_RESULTS.md).

Read-only quarantine inspection now enforces read-only UTC transactions and
returns bounded metadata, receipt presence and an opaque row-state observation
version. The [audited reconciliation design](RECONCILIATION_DESIGN.md) is ready for
review, but no resolution/reset/resend, audit write API or operator grant is
enabled. Owner approval is required before enabling any such operation. The row
hash is not authorization or proof of non-delivery; absent receipt is not proof
that Telegram did not accept a send. A commit error may still hide a successful
commit: inspect durable state, never blindly replay.

Only the exact previously authorized schema input was accessed read-only. All
runtime checks used pinned daemon/image and fresh PostgreSQL 17, tmpfs/read-only
root, no network/ports/host mounts; teardown passed with original running container
IDs unchanged. No Telegram API call, n8n/full completed integration rerun,
production credential/service access, deployment or merge. Git metadata is still
read-only; current changes are uncommitted. Source scan/diff review passed.

Owner commit commands after review (explicit safe paths only):

```bash
git status --short
git diff -- dincharya/reminders.py dincharya/reminder_adapters.py telegram-gateway/gateway.py telegram-gateway/reminder_handlers.py telegram-gateway/README.md database/migrations/README.md docs/HANDOFF.md docs/MILESTONE2_PLAN.md docs/DECISIONS.md docs/ROADMAP.md docs/WSL2_REMINDER_ACCEPTANCE.md tests/integration/application_runner.py tests/integration/focused_application_runner.py tests/sql/README.md tests/test_migrations.py tests/test_reminder_adapters.py tests/test_reminder_worker.py
git add -- database/migrations/0004_telegram_receipts.sql database/migrations/README.md dincharya/reminders.py dincharya/reminder_adapters.py telegram-gateway/gateway.py telegram-gateway/reminder_handlers.py telegram-gateway/README.md docs/HANDOFF.md docs/MILESTONE2_PLAN.md docs/DECISIONS.md docs/ROADMAP.md docs/WSL2_REMINDER_ACCEPTANCE.md docs/RECONCILIATION_DESIGN.md docs/M2_RECEIPTS_ADVERSARIAL_RESULTS.md tests/integration/application_runner.py tests/integration/focused_application_runner.py tests/integration/adversarial_checks.py tests/sql/gregorian_adversarial.sql tests/sql/telegram_receipts.sql tests/sql/README.md tests/test_migrations.py tests/test_reminder_adapters.py tests/test_reminder_worker.py tests/test_reminder_gateway_preflight.py
git diff --cached --check
git diff --cached
git commit -m "feat: persist lease-checked Telegram receipts and expand API regression coverage"
```

Next significant gate: approve the proposed audited resolution policy before any
operator mutation/resend is enabled; no action is authorized by inspection alone.
Independent remaining work includes recovery restart/outage permutations, source
adoption/provenance, Panchang provider/tradition/reference decision and isolated
operational acceptance. Do not repeat completed live acceptance or use production.

## Last successful evidence

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

