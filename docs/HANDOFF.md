# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint

Branch `development/m2-recovery-acceptance`, pushed base `d987b69` (receipt and
adversarial checkpoint). Existing uncommitted reconciliation work was preserved,
reviewed and completed after interrupted sessions. [Issue #2](https://github.com/vasu1765/dincharya-ai/issues/2)
tracks all Milestone 2, including Hindu Panchang and operational acceptance before
other orchestrators. PR #1 is merged; no deployment or main merge here.

The owner approved **confirmed already-delivered reconciliation in isolated
synthetic PostgreSQL only**. New migration 0005 installs private immutable
evidence, independent destination pins, expiring explicit permits, append-only
audit and a default-disabled synthetic gate. A dedicated authenticated DB login
supplies operator identity; payload actor IDs/GUCs/SET ROLE cannot substitute it.
The API locks configuration and the delivery, validates a fresh UTC row version,
and atomically records sent state, receipt and audit. Exact replay is idempotent;
changed replay, duplicate receipt, invalid evidence, stale/leased/resolved rows
reject safely. Separate NOLOGIN executors and scoped operator/worker wrappers
preserve least privilege. Original migrations 0001–0004 and worker functions are
unchanged; restricted worker mode is opt-in. No historical receipt backfill.

Retained successful `reconciliation-concurrency` evidence covers actual SCRAM
logins/wrong passwords, privilege boundaries, evidence/permit/destination checks,
concurrent decisions and replay, audit fault/caller rollback, receipt uniqueness,
history preservation and normal worker acknowledgement. 24 focused unit tests
passed in the completed checkpoint. See [sanitized evidence](M2_RECONCILIATION_RESULTS.md)
and [design/trust boundaries](RECONCILIATION_DESIGN.md).

Resume security review fixed permit expiry during a row-lock wait and hardened
synthetic server statement/error/parameter/duration logging around password DDL.
Only the new `reconciliation-review` runtime case was run: effective logging and
SCRAM negative authentication passed; a permit valid before a confirmed lock wait
expired before lock release and rejected with no delivery/audit writes. Seven
affected renderer/runner offline tests passed. Completed concurrency/receipt/2C/
live acceptance suites were not repeated. Explicit safe-source scan and diff
checks and changed-Python AST checks passed; the scanner was not weakened. GitHub
issue #2 was updated with these results and remaining gates. No full-suite rerun
is claimed.

All runtime checks verified pinned daemon/image, fresh PostgreSQL 17, tmpfs and
read-only root, no network/ports/host mounts, disabled final synthetic gate,
container removal and unchanged original running container IDs. Only the exact
authorized schema file was read unchanged. No Telegram calls, resend/reset,
production credentials/services, deployment or merge. Production reconciliation
remains disabled, with no gateway resolution command or production provisioning.
Trusted real evidence/destination/permit authority, production identity/TLS and
operational procedures remain design/approval gates; admin tamper resistance and
external exactly-once delivery are not claimed.

Git metadata is mounted read-only, confirmed with `findmnt`; no bypass, stage or
commit attempted. The exact safe-file list is the `git add` below. Run in your
normal WSL terminal after reviewing the untracked new files as well as the diff;
verify the branch is still `development/m2-recovery-acceptance` and the index has
no unrelated changes. These commands do not push, deploy or merge:

```bash
git status --short
git diff --check
git diff -- AGENTS.md database/migrations/0005_synthetic_reconciliation.sql database/migrations/README.md dincharya/reconciliation.py dincharya/reminder_adapters.py tests/integration/focused_application_runner.py tests/integration/reconciliation_checks.py tests/test_migrations.py tests/test_reconciliation.py tests/sql/README.md docs/DECISIONS.md docs/HANDOFF.md docs/MILESTONE2_PLAN.md docs/ROADMAP.md docs/RECONCILIATION_DESIGN.md docs/M2_RECONCILIATION_RESULTS.md
git add -- \
  AGENTS.md \
  database/migrations/0005_synthetic_reconciliation.sql \
  database/migrations/README.md \
  dincharya/reconciliation.py \
  dincharya/reminder_adapters.py \
  tests/integration/focused_application_runner.py \
  tests/integration/reconciliation_checks.py \
  tests/test_migrations.py \
  tests/test_reconciliation.py \
  tests/sql/README.md \
  docs/DECISIONS.md \
  docs/HANDOFF.md \
  docs/MILESTONE2_PLAN.md \
  docs/ROADMAP.md \
  docs/RECONCILIATION_DESIGN.md \
  docs/M2_RECONCILIATION_RESULTS.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "feat: add synthetic audited delivery reconciliation"
```

Next work: remaining targeted 2E restart/outage recovery and operational planning,
review full 2D exit evidence, source-adoption provenance, and the owner decision
on Panchang source/tradition/reference fixtures. No production enablement or
resend is authorized. Avoid repeating completed acceptance without a relevant
functional change. Complete all Milestone 2 before other orchestrators.

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

