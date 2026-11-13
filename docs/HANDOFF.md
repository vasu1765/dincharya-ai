# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint — lunar PostgreSQL T00–T26 passed

Pushed implementation HEAD `599113826a6052fa89389f3b4c61a3b9c370a559` verified on
`development/m2f-postgres-integration`; entry working tree clean. Git metadata is
still mounted read-only. New fixes/evidence are uncommitted; no Git bypass,
stage/commit/push attempted. Previous “uncommitted implementation/runtime gated”
instructions are superseded for this owner-authorized isolated acceptance cycle.

- Owner authorized the exact pinned daemon/schema lunar command and demonstrated
  defect fixes. Scoped sandbox execution permission granted for Docker access;
  no socket permission changes. Only named schema read, no other backup artifacts.
- Final run: **T00–T26 all passed, exit0**, migrations0001–0008 installed in fresh
  network-none/no-port/read-only-root/tmpfs-only disposable PostgreSQL17. Daemon
  `44c1ef83-c50e-4ecc-8f19-4b112bc40f29` verified before creation.
- Synthetic API proposal/approval->native projection->refresh->real server-clock
  due claim->synthetic receipt passed; no actual Telegram transport. Concurrency,
  stale/ABA, audit rollback/replay, replacement/cancel/history and disposable
  postmaster crash/restart tests passed. SCRAM and scoped privileges retained.
- Demonstrated42702 fixed additively in0007: qualify calculation local command
  binding.42P01 fixed in0008: set reviewed baseline recurrence-sync invoker
  helper’s safe search_path; preserve its body/ACL/owner/security mode.
  Committed0001–0006 files remain byte-identical.
- Runner now extracts sanitized function/line diagnostics and handles terse/verbose
  SQLSTATE separators. Added focused SQLSTATE regression; **20 offline tests pass**.
  No relaxation of authorization, isolation, history or concurrency checks.
- Every diagnostic/final disposable run verified cleanup and unchanged original
  running-container IDs. Existing PostgreSQL/n8n services untouched. No live tests,
  production, deployment, merge or private2B access. No unrelated suites repeated.
- [Results](M2F_POSTGRESQL_RESULTS.md) records failures, corrections, complete
  acceptance and limits. Architecture/decisions/roadmap/plan and GitHub issue2
  updated. AGENTS unchanged.

No unresolved synthetic acceptance failure. Next separate work: validated preview
input adoption, advance/multiple reminder slots, astronomical release gates and
operational acceptance; no scheduling/production/workflow adoption inferred.
Do not repeat successful acceptance without materially affected code.

Safe consolidated normal-WSL commands (13 files; review index before commit):

```bash
git branch --show-current
git status --short
git diff --check
git add -- \
  database/migrations/0007_lunar_calculation_binding.sql \
  database/migrations/0008_lunar_projection_trigger_path.sql \
  database/migrations/README.md \
  tests/integration/focused_application_runner.py \
  tests/test_lunar_postgres.py \
  tests/test_focused_application_runner.py \
  docs/M2F_POSTGRESQL_RESULTS.md \
  docs/HANDOFF.md \
  docs/ARCHITECTURE.md \
  docs/DECISIONS.md \
  docs/MILESTONE2_PLAN.md \
  docs/ROADMAP.md \
  docs/M2F_POSTGRESQL_DESIGN.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "fix: validate synthetic lunar PostgreSQL acceptance"
git push origin development/m2f-postgres-integration
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

