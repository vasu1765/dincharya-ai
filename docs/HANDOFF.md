# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint — authorized isolated in-memory lunar contract, stop offline

Base `9eaf859ccd6fe99cb77a02d3758817ff551399c7`; entry clean on
 development/m2f-skyfield-feasibility. Owner created separate
`development/m2f-memory-contract`; agent verified it, with clean tree before edits.
Old uncommitted34b6270-base instructions superseded. Git metadata remains mounted
read-only; no stage/commit/push/bypass attempted. Current changes uncommitted;
no new commit SHA can be reported until owner executes the explicit commands.

- Owner authorized this in-memory proposal/approval/ledger simulation only. No DB,
  n8n, Telegram, actual delivery or scheduling enablement. AGENTS unchanged.
- Separate immutable UUID series for synthetic birthday/wedding share the same
  lunar key without collision. Ledger key is series UUID + existing logical key.
- Reuses LunarRule/logical_key/research comparison boundary and DeliveryReceipt;
  no duplicate astronomy, worker/lease/retry implementation. SQL approval source
  reviewed for snapshot/ownership/atomicity expectations; no SQL executed.
- Immutable proposals, approval action/snapshots and ledger/history records.
  Explicit owner capability, per-occurrence approval, observation/candidate-rule
  generations, stale/ABA/action replay guards. Changed dates/rules require review;
  already materialized entries cannot be replaced, even after new approval.
- Validated batch is atomic in process; repeated submission/recalculation/overlap
  idempotent. Unsupported/unselected/ambiguous/skipped input rejects; empty result
  no-op. Test-only sent/uncertain fixture records/receipts immutable, no resend path.
-29 focused tests pass0.480s (15 adapter+2 comparison+12 mocked worker regressions).
  Stale/unauthorized replay strengthened test passes0.001s. Red forged2030 date
  outside2023 physical interval rejected after adding interval-containment check.
- Actual engine-to-adapter overlap test runs offline.11 accepted reference/result
  files unchanged; astronomical model/dependencies/diagnostics untouched. No
  unrelated integration/accuracy/coordinate suite rerun or new packages/data.

See [contract/API/acceptance/risks](M2F_MEMORY_CONTRACT.md),
[tests](../tests/panchang/test_memory_contract.py),
[synthetic fixtures](../tests/panchang/fixtures/memory-contract.synthetic.json) and
[results](../prototypes/panchang/memory-contract-results.json). Source-safety,
AST/JSON/link/diff and accepted-evidence checks pass; GitHub issue2 updated.

Readiness: in-memory contract accepted by focused tests, ready for separate owner
review of PostgreSQL mapping/transaction/auth/locking design and finite synthetic
acceptance plan. NOT ready for DB execution, migration, persistence/delivery or
live adoption. Trusted capability is not production auth; no concurrency/durability,
conflict checks or ledger replacement. Existing n8n/SQL/leases/history untouched.
No production/private backup/2B access, migration, live Telegram, deployment/main
merge or other orchestrator. Neutral profile/consolidated future observances stay.
Stop after offline checkpoint; any next DB design/execution scope needs approval.

Normal WSL commands (branch already created),14 explicit safe files; inspect index:

```bash
git branch --show-current
git status --short
git diff --check
git add -- \
  prototypes/panchang/memory_contract.py \
  prototypes/panchang/memory-contract-results.json \
  tests/panchang/test_memory_contract.py \
  tests/panchang/fixtures/memory-contract.synthetic.json \
  docs/M2F_MEMORY_CONTRACT.md \
  docs/HANDOFF.md \
  docs/ARCHITECTURE.md \
  docs/DECISIONS.md \
  docs/MILESTONE2_PLAN.md \
  docs/ROADMAP.md \
  docs/M2F_RECURRENCE_PREVIEW.md \
  docs/M2F_FEASIBILITY_RESULTS.md \
  docs/M2F_PREINTEGRATION_ASSESSMENT.md \
  prototypes/panchang/README.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "feat: add isolated in-memory lunar approval contract"
git push -u origin development/m2f-memory-contract
git rev-parse HEAD
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

