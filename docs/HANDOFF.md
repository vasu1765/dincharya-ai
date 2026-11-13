# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint — PostgreSQL lunar design, no implementation

Verified pushed HEAD `0304de6a5ee140c313eb4aae6c2d18a35b0e7e99` on
`development/m2f-memory-contract`; entry working tree clean. The prior in-memory
checkpoint is committed/pushed, superseding its old uncommitted instructions.
Git metadata remains read-only; no bypass, stage, commit or push attempted here.

Owner authorized design/review only. See [PostgreSQL mapping, authorization,
transaction design and finite acceptance plan](M2F_POSTGRESQL_DESIGN.md).

- Proposes one native managed Gregorian one-off projection per logical lunar
  occurrence, scoped by immutable personal series UUID. Reuses existing requests,
  occurrence generator, conflicts, reminder ledger and worker; no second queue.
- Seven proposed metadata/authority/audit tables; no executable DDL or migration.
  Trusted session identity, explicit lunar dispatch, mapped-event write barriers,
  shared scheduler mutex, fresh snapshots and atomic approval/materialization.
- Date replacement restricted to never-attempted work, same projection ID;
  cancellation tombstones prevent revival. Sent/uncertain history stays immutable.
  Legacy event_date synchronization is an explicit future implementation check.
- Memory source reviewed against migrations0001–0005 and reminder contracts.
  No demonstrated offline defect; no source/model/reference files changed.
  Atomic SQL approval, committed rule revisions and conflict handling are proposed
  differences, not claimed in-memory capabilities.
- T00–T26 is a finite future synthetic acceptance plan, not executed evidence.
  No PostgreSQL, Docker, Telegram, n8n, private inputs or production access.
- Owner approval required for projection/schema/auth contract, replacement and
  cancellation policy, and one-at-event reminder scope for initial synthetic tests.
  Advance/multiple reminders remain required for full Milestone2. Database execution
  needs separate authorization; no scheduling/engine adoption is implied.

Validation: four offline migration-renderer tests pass. Explicit documentation
source-safety, links, syntax/evidence immutability and diff checks are recorded at
this checkpoint. Existing29 in-memory/regression passes remain historical evidence;
unchanged tests and unrelated integration suites were not rerun.

Readiness: design ready for owner review; PostgreSQL implementation/execution is
not authorized. No architectural choice in the proposal is recorded as adopted.
GitHub issue2 updated with design status and approval gates. AGENTS unchanged.

Exact safe commands in normal WSL (review index before committing):

```bash
git branch --show-current
git status --short
git diff --check
git add -- docs/M2F_POSTGRESQL_DESIGN.md docs/HANDOFF.md docs/ARCHITECTURE.md docs/DECISIONS.md docs/MILESTONE2_PLAN.md docs/ROADMAP.md docs/M2F_MEMORY_CONTRACT.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "docs: design lunar PostgreSQL mapping and acceptance"
git push origin development/m2f-memory-contract
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

