# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint

Branch `development/m2-recovery-acceptance`, committed base `3d46d8e`. The
reconciliation checkpoint is committed; the working tree was clean at entry.
PR #1 is merged. [Issue #2](https://github.com/vasu1765/dincharya-ai/issues/2)
tracks all Milestone 2, including Panchang and operational acceptance before
other orchestrators. No production authorization follows from these results.

The missing 2E worker reconnect/postmaster outage matrix now passed in the new
`restart-recovery` case. Committed sent/uncertain/leased/rejected/cancelled state
survived immediate postmaster shutdown/start unchanged; an interrupted uncommitted
claim rolled back. New SCRAM worker processes resumed safe rejection backoff at
its boundary, quarantined exact lease expiry, rejected stale acknowledgements,
recovered the inclusive lookback edge, excluded outside work, preserved sent/
uncertain history and stable replanning identity, and suppressed duplicate claims.
No application defect was demonstrated; no migration/worker behavior changed.

The case uses the existing fresh disposable PostgreSQL infrastructure with a
case-only supervisor to keep container tmpfs alive while the postmaster stops.
It does not restart the container or establish persistent-volume/host recovery.
Before/after restart, host HBA rules required SCRAM and trust was limited to
container-local Unix sockets; incorrect passwords rejected. Worker/operator ACLs,
secret-safe server logging, immutable audit infrastructure and the disabled
reconciliation gate were preserved. Passwords remained stdin/environment-only,
never values in argv, published output or repository files.

One new Docker case and three affected offline runner tests passed. Existing
lookback/recovery SQL, receipt/concurrency/reconciliation, n8n and live Telegram
acceptance were not repeated. Pinned daemon/image and exact schema-only input
were verified unchanged; isolation/teardown passed and original running container
IDs stayed unchanged. No production access, Telegram sends, reset/resend,
deployment or merge. Explicit source-safety, changed-Python AST and safe-file
whitespace/diff checks passed. GitHub issue #2 was updated; no open PR was found
for this branch. See [evidence and 2D gap matrix](M2_RESTART_RECOVERY_RESULTS.md).

2D authorization/stale/conflict/race and D10 boundaries are satisfied in existing
covered cases. Pending: full weekly/yearly and year-transition public API fixtures,
series recurrence changes with existing overrides/future reminders, and trusted
managed-v2 workflow adoption. Bounded conflict horizons/unsupported overnight
schedules are intentional current limits. 2E controlled-clock restart matrix is
covered; gateway supervision, host/disk/restore and broader operational acceptance
remain. No external exactly-once or production-readiness claim is made.

Production reconciliation remains disabled; real evidence authority/provisioning
and production identity/TLS need separate review. All resends remain prohibited.
Next: targeted remaining 2D fixtures and 2G recovery/operational planning, then
owner-gated source adoption and Panchang provider/tradition/reference decisions.
No significant architecture decision arose in this test-only task.

Git metadata is confirmed mounted read-only; no stage/commit or bypass attempted.
Run these exact eight-safe-file commands in your normal WSL terminal after
checking the branch/index and reviewing the new untracked file contents. No push,
deployment or merge is included:

```bash
git status --short
git branch --show-current
git diff --check
git add -- \
  tests/integration/focused_application_runner.py \
  tests/integration/recovery_checks.py \
  tests/test_focused_application_runner.py \
  tests/sql/README.md \
  docs/HANDOFF.md \
  docs/MILESTONE2_PLAN.md \
  docs/ROADMAP.md \
  docs/M2_RESTART_RECOVERY_RESULTS.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "test: verify synthetic reminder restart and outage recovery"
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

