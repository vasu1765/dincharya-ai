# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint — synthetic lunar E2E passed

Pushed base `5cf007f536aaaac2708238f20b1add10f2c27489` verified, entry tree clean.
Owner created and agent verified `development/m2f-synthetic-e2e`. Git metadata
remains mounted read-only; new15-file checkpoint is uncommitted, no Git write or
bypass attempted. Previous “uncommitted PostgreSQL acceptance” commands superseded.

- Owner authorized isolated synthetic request->preview->explicit approvals->native
  PostgreSQL projection->existing worker->simulated delivery->receipt journey.
  Scoped sandbox Docker permission granted for the exact new runner command.
- **E01–E05 all passed, exit0** through real native n8n webhook, a separate Python
  process, existing SyntheticLunarPostgres/PostgresReminders/process_batch and real
  scoped SCRAM PostgreSQL sessions. No repository/DB success mocks in runtime.
- Invented birthday fixtures only; astronomy_enabled=false, no model/predictions.
  Separate rule/occurrence approvals, stale/rejected decisions and cancellation
  tested. Three eligible delivery attempts recorded exactly once: sent+receipt,
  definitive failed (then approved cancellation), and uncertain. No other sends.
- Two actual worker-process/n8n restart cycles, unchanged PostgreSQL ID/start time,
  repeated/concurrent ticks and exact durable delivery history pass. Simulated
  transport has no dedupe masking worker defects. No second scheduler/worker.
- Demonstrated SCRAM assertion initially failed: older2C initdb loopback TCP trust.
  Added explicit host SCRAM/local socket trust to ONLY test compose environment;
  reviewed validator digest updated. No check weakened. Final isolation/cleanup
  and original unrelated running-container IDs unchanged; failed run also cleaned.
- **46 focused offline tests pass** (7 new+39 affected runner).14 explicit source
  scans pass; shared runner has two pre-existing variable-reference false positives,
  human-reviewed (only its digest changed). Scanner rules unchanged. AST/JSON/link/
  diff/immutability checks pass. No T00–T26 or old cadence/live suite
  rerun. Existing application migrations, engine, gateway and worker untouched.
- [Actual evidence/command/limits](M2F_SYNTHETIC_E2E_RESULTS.md), architecture,
  D23, milestone plan, roadmap and integration README updated; GitHub issue2
  updated. AGENTS unchanged. No production, live Telegram/n8n service, private2B,
  deployment or main merge. Only the named authorized schema was read.

No unresolved synthetic E2E failure. First private Telegram test is NOT ready:
needs reviewed real authenticated gateway lunar-command/driver/transport binding
(the Docker/stdio/psql bridge is test instrumentation), scoped credential setup
outside Git and fresh explicit dedicated-bot delivery approval. Scheduling still
requires explicit owner approval; actual astronomy remains disabled. General
calendar/advance-slot/operational adoption and other orchestrators remain gated.

Normal-WSL consolidated commands (15 explicit safe files):

```bash
git branch --show-current
git status --short
git diff --check
git add -- \
  tests/integration/compose.json \
  tests/integration/runner.py \
  tests/integration/e2e_bridge.js \
  tests/integration/e2e_n8n_client.js \
  tests/integration/e2e_worker.py \
  tests/integration/e2e_fixture.sql \
  tests/integration/synthetic_e2e_runner.py \
  tests/test_synthetic_e2e.py \
  tests/integration/README.md \
  docs/M2F_SYNTHETIC_E2E_RESULTS.md \
  docs/HANDOFF.md \
  docs/ARCHITECTURE.md \
  docs/DECISIONS.md \
  docs/MILESTONE2_PLAN.md \
  docs/ROADMAP.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "test: integrate synthetic lunar reminder end to end"
git push -u origin development/m2f-synthetic-e2e
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

