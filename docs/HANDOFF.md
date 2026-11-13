# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint — lunar PostgreSQL source ready; runtime gated

Verified pushed design HEAD `81acd6a8240f474b0bdabf4d73a79f1433b9a08c`, clean entry
on development/m2f-memory-contract. Owner created and agent confirmed
`development/m2f-postgres-integration`. Metadata mount is read-only; no Git write,
bypass, stage/commit/push attempted. Current implementation is uncommitted.

Latest owner authorization supersedes the prior design-only implementation gate;
it explicitly withholds PostgreSQL connections/Docker execution. See
[implementation and evidence](M2F_POSTGRESQL_RESULTS.md),
[original design/T00–T26](M2F_POSTGRESQL_DESIGN.md) and D21.

- Added0006 synthetic-only migration, six private tables (actions also store
  immutable approved revisions), trusted session identity, scoped executor and
  native one-off projection approval. Migrations0001–0005 byte-preserved.
- Explicit propose/inspect/approve/reject, calculation replay and fresh observation/
  rule/occurrence review fingerprints. Native child/projection/audit atomicity;
  stable typed series/key/event identities; synchronized compatibility event_date.
- Mapped-event/request/rule/override barriers, limited preserved-body wrappers,
  no raw caller DML or executor membership. Immutable profile descriptors hash-bound;
  producer/owner/worker separated. No production ACL rollout or auth adoption.
- Never-attempted replacement only, same event ID; any sending blocks edits.
  Cancellation tombstones/explicit bounded manifests prevent revival; attempted
  history/receipts preserved, no resend/reset. Identity remapping unsupported.
- Added opt-in parameterized Python adapter and T00–T26 runtime assertions to the
  existing pinned standalone synthetic runner. New case isolated from old cases.
  Includes genuine API->refresh->due claim->synthetic receipt, parallel decisions/
  workers, controlled mutex waits, audit-fault rollback and disposable DB restart.
- **19 offline tests pass** (8 adapter,4 packaging,4 renderer,3 affected preflight).
  Python AST/SQL lexical/source-safety/diff/evidence immutability checks pass.
  These are NOT PostgreSQL grammar/runtime/ACL or concurrency pass claims.
  Old unrelated model/memory/2C/2D/2E/n8n/live suites not rerun.
- No DB connection, Docker, Telegram, n8n, private baseline/2B, production, deploy
  or merge. AGENTS unchanged. GitHub issue2 updated with runtime-pending status.

Next action requiring owner authorization: execute ONLY the exact `--case lunar`
command in M2F_POSTGRESQL_RESULTS.md, using the named schema and pinned daemon in
fresh disposable PostgreSQL. Do not activate scheduling. Fix/rerun materially
failed runtime cases within that later authorization. Current remaining risks:
SQL/catalog/ACL compatibility and real transaction/race/restart evidence; advance
slots, broader astronomical adoption and operational acceptance remain open.

Safe normal-WSL commit commands (14 files; inspect index before commit):

```bash
git branch --show-current
git status --short
git diff --check
git add -- \
  database/migrations/0006_synthetic_lunar_approval.sql \
  database/migrations/README.md \
  prototypes/panchang/postgres_contract.py \
  tests/integration/focused_application_runner.py \
  tests/integration/lunar_checks.py \
  tests/test_lunar_postgres.py \
  tests/test_focused_application_runner.py \
  docs/M2F_POSTGRESQL_DESIGN.md \
  docs/M2F_POSTGRESQL_RESULTS.md \
  docs/HANDOFF.md \
  docs/ARCHITECTURE.md \
  docs/DECISIONS.md \
  docs/MILESTONE2_PLAN.md \
  docs/ROADMAP.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "feat: add synthetic PostgreSQL lunar approval integration"
git push -u origin development/m2f-postgres-integration
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

