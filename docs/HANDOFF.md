# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Reminder gateway development branch

GitHub main at `b80a91d8` contains the recurrence/reminder foundations described
below. The old unstaged-files checkpoint is historical for the earlier workspace.

The opt-in gateway uses PostgreSQL proposal, decision, claim and finish functions.
A private owner command creates a one-time proposal. Only a separate owner
approval schedules it. The Telegram adapter uses the configured private chat.
See [isolated reminder acceptance](../telegram-gateway/README.md).
Ten focused offline Python tests passed, including adapter transactions and
Telegram response classification. The added SQL approval and retry cap checks,
expanded concurrency checks and test-bot acceptance require runtime verification.

## Historical authority and approval gate

On 2026-11-13 the user resumed work and authorized reviewing changed files and
staging only safe project source, migrations, tests and documentation. A commit
requires explicit approval of the proposed file list/message; do not commit yet.
After the approved commit, prioritize completing 2D/2E and the first end-to-end
Telegram reminder within existing boundaries. Production changes and use of the
production bot remain excluded; a test transport/bot needs the appropriate scope.
Do not rerun previously successful integration tests without relevant code changes.
The last application integration passed. New runner checks listed below remain
integration-unverified. Preserve all pre-existing working-tree work.

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
  transport adapters, workflow/gateway wiring, operator resolution of uncertain
  sends and deployment remain future integration work. A batch abort can leave
  remaining claims to expire into quarantine; external exactly-once is not claimed.
- ApplicationRunner's **new checksum-corruption rejection**, **parallel duplicate
  decision check**, **competing reminder-claim check** and final concurrent
  acknowledgement are source-reviewed/syntax-checked only, not runtime verified.
  They were added after the last passing SQL integration. Existing concurrency
  safety assertions must not be presented as passing multi-session evidence.
- Retry exhaustion, broad outage/recovery permutations, adversarial API cases,
  legacy API interaction with managed series, and worker transport wiring need
  further focused coverage before declaring all of 2D/2E complete.

## Source/provenance boundaries

Only the exact application-schema.sql path authorized in the conversation was
opened, read-only. No backup directory, n8n.dump, credential table or other backup
artifact was scanned. The three named repository docs identify **no exact original
review/provenance manifest path**. Manifest location remains missing; do not guess
or search private directories. The user's source authorization does not certify
all schema functions or authorize production application/source promotion.

Git status verified for the consolidated report: branch main; latest commit
ceeba98 (feat: complete offline source tooling and integration preparation).
62e96e6 is the earlier 2A tooling checkpoint, not current HEAD. The integration,
migration, worker, tests and documentation changes remain uncommitted; current
staging status is determined by git status during the commit-preparation task.
2C is complete for its synthetic scope; 2D and 2E are partially complete and are
not production-ready. No tests or Docker operations were rerun for this report.

Historical 2B evidence remains: four
current workflows, 94 history versions, two structural candidates; current and
published bodies remain separate; seven Code bodies were neither executed nor
cleared. No complete production workflow/schema baseline has been adopted in Git.

## Commit preparation

Review explicit safe paths only: docs/HANDOFF.md, docs/ROADMAP.md,
docs/ARCHITECTURE.md, docs/native-scheduler-state.md,
database/migrations/README.md, tests/integration/README.md,
tests/integration/compose.json, tests/integration/runner.py,
tests/integration/api-client.js, tests/integration/test-api-client.js,
tests/integration/application_runner.py, tests/test_integration_config.py,
tests/test_integration_runner.py, database/migrate.py,
database/migrations/0001_gregorian_occurrences.sql,
database/migrations/0002_occurrence_reminders.sql, tests/sql/gregorian.sql,
tests/sql/reminders.sql, tests/test_migrations.py, dincharya/__init__.py,
dincharya/reminders.py and tests/test_reminder_worker.py.

Keep temporary debugging scripts, daemon pins, logs, raw schema and private source
outside Git. Stage only the reviewed paths above if Git metadata is writable;
never escalate or relocate .git to bypass metadata restrictions. No commit until
user approval. Proposed subject: feat: add isolated recurrence and reminder foundations.

The unchanged safe-source heuristic flags generated/in-memory and invented test
password assignments in integration source. These matches were manually reviewed
as false positives; do not weaken the scanner or report an unconditional code-scan
pass. Documentation, migration and application source scan results are recorded
in the final checkpoint report; human privacy/diff review is still required.

## 2026-11-13 commit-preparation result

All 22 modified/untracked candidate files were reviewed as explicit regular text
source, migrations, tests or documentation. No credentials, raw/private baseline
data, logs, backups, binary files or generated artifacts were found in that
inventory. Eighteen files passed the safe-source scanner; six generated/in-memory
or invented password assignments in four integration files were manually reviewed
as false positives. No scanner was weakened. No integration tests were rerun.

Staging was explicitly authorized, but git add failed because .git/index.lock
cannot be created on the read-only Git filesystem. Nothing was staged or committed.
Do not escalate, relocate .git or alter permissions to bypass this restriction.
The reviewed file list above and proposed commit message await user approval;
staging/committing additionally require operator-provided writable Git metadata.

Proposed message: feat: add isolated recurrence and reminder foundations

- Add Gregorian change/occurrence migrations and an injected reminder worker.
- Add isolated n8n/application runners, synthetic tests and migration checksums.
- Record passing integration evidence and outstanding 2D/2E acceptance gaps.

The expanded concurrent/checksum-corruption runtime checks remain unverified.
After an approved commit, prioritize their focused verification, remaining 2D/2E
acceptance, and a first end-to-end reminder using a separately authorized test
Telegram transport/bot; do not use or modify production.
