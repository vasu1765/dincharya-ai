# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint

Development branch: `development/m2-recovery-acceptance`, committed base `120b28a`.
PR #1 merged at `f3db2ff`; acknowledgement recovery/roadmap work is committed and
pushed. ALL Milestone 2, including Hindu Panchang and operational acceptance,
remains required before other domains/orchestrators. Track [issue #2](https://github.com/vasu1765/dincharya-ai/issues/2)
and [plan](MILESTONE2_PLAN.md).

Current uncommitted task implements owner-approved [D10](DECISIONS.md): reject
legacy update/remove submissions and approvals for managed series; require a fresh
v2 proposal. A new test first demonstrated legacy approval bypassing a changed
managed override. Additive migration 0003 now guards the original public proposal
and decision entry points plus direct legacy request submission. Current ownership
is checked under the v2 advisory lock, covering requests created before conversion.
Unauthorized requests retain a generic response; authorized blocked approvals get
only the sanitized v2-required reason and stay pending for explicit discard.
Original legacy bodies, signatures, ACLs, ownership and execution properties are
preserved; existing migration/baseline bytes remain unchanged. No new privileges,
public bypass aliases or production operations.

Focused evidence: three new SQL cases passed (coexistence, managed transition/
boundary and targeted recovery), plus a multi-session conversion/legacy-decision
case observing blocked waiters. Genuine legacy updates/removals, stale rejection,
new submissions, force/authorization, pending pre-conversion requests and continued
v2 approval/override/replay protection passed, including forged version tags and
noncanonical approval attempts. Recovery covers exact six-hour and
expiry boundaries, stale ack, sent/quarantine history, cancelled-work replanning
and no automatic resend. Eight adapter tests, four migration renderer tests and
three new runner preflight tests passed. Do not report these as a full suite run.

New `PostgresReminders.list_quarantined` is bounded read-only metadata inspection,
with no payload/title/chat/token/error exposure and no reset/resend capability.
It is adapter-tested, not a completed operator reconciliation interface. See
[sanitized results](M2_COMPATIBILITY_RECOVERY_RESULTS.md) for test limits and fixes.
The PostgreSQL-only focused runner selects named cases, verifies daemon/image,
uses fresh tmpfs/no-network/no-port/no-mount test resources, and cleans up. Every
completed run preserved original running container IDs; final prefix audit found
no leftover disposable containers after the interrupted call. No Telegram/n8n or
completed full integration suite was repeated. Only the exact previously
owner-authorized schema input was read, unchanged; no backup search or production
credential/service access occurred.

Git metadata remains read-only; no staging/commit/push attempted here. Owner
commands after reviewing explicit safe files:

```bash
git diff -- database/migrations/README.md dincharya/reminder_adapters.py docs/DECISIONS.md docs/HANDOFF.md docs/MILESTONE2_PLAN.md docs/ROADMAP.md docs/WSL2_REMINDER_ACCEPTANCE.md telegram-gateway/README.md tests/integration/application_runner.py tests/test_migrations.py tests/test_reminder_adapters.py tests/sql/README.md
git status --short
git add -- database/migrations/0003_managed_legacy_boundary.sql database/migrations/README.md dincharya/reminder_adapters.py docs/DECISIONS.md docs/HANDOFF.md docs/MILESTONE2_PLAN.md docs/ROADMAP.md docs/WSL2_REMINDER_ACCEPTANCE.md docs/M2_COMPATIBILITY_RECOVERY_RESULTS.md telegram-gateway/README.md tests/integration/application_runner.py tests/integration/focused_application_runner.py tests/integration/legacy_boundary_checks.py tests/sql/legacy_coexistence.sql tests/sql/legacy_managed_boundary.sql tests/sql/reminder_recovery.sql tests/sql/README.md tests/test_migrations.py tests/test_reminder_adapters.py tests/test_focused_application_runner.py
git diff --cached --check
git diff --cached
git commit -m "fix: enforce managed-series legacy boundary and test recovery"
```

Next: remaining 2D adversarial API matrix; P3 nullable chat/message receipts and
lease-checked acknowledgement, then explicit audited resolution design. No new
architecture decision is needed for this patch. Enabling resolution/resend is not
implicit in read-only inspection; Panchang source/tradition/geographic/reference
policy remains a later owner decision. Do not merge, deploy or repeat live sends.

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

