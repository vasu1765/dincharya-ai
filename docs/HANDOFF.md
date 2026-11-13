# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint

2026-11-13: GitHub confirms PR #1 merged into main at
`f3db2ff600dbb417e8bd2c553aad5388697cbd9e`; merged feature head is `1c60fe1`.
This includes the accepted single test-bot reminder and tested 429 quarantine.
Owner reconfirmed ALL Milestone 2, including Hindu Panchang scheduling and
operational acceptance, must finish before other domains or orchestrators.
See [prioritized implementation plan](MILESTONE2_PLAN.md), with explicit 2B/2D/2E
source/test gaps and milestone acceptance criteria.
GitHub tracking: [Milestone 2 completion issue #2](https://github.com/vasu1765/dincharya-ai/issues/2).

Owner completed synchronization and branch creation in normal WSL after the
sandbox fetch failed on read-only Git metadata. Verified local main and
`development/m2-recovery-acceptance` both start at `f3db2ff`, initially clean.
No escalation or alternate Git store was used.

Implemented the first focused 2E recovery fix: database finish exceptions and
lease loss now raise sanitized DeliveryUncertain, without retrying transport or
continuing the remaining claimed batch. Reproduced the prior raw-exception gap.
Added tests across accepted/rejected/unknown send outcomes and multi-claim abort;
all **17 focused reminder tests passed**. No services/private inputs needed.
Remaining claims still expire into quarantine; no active lease reset was added.
Source scan and diff review passed. Existing architecture/migrations unchanged.

Git metadata remains read-only. Owner commands to record the reviewed changes:

```bash
git diff -- AGENTS.md dincharya/reminders.py tests/test_reminder_worker.py docs/HANDOFF.md docs/ROADMAP.md docs/ARCHITECTURE.md docs/DECISIONS.md docs/DEVELOPMENT_POLICY.md
git diff --no-index -- /dev/null docs/MILESTONE2_PLAN.md
git add -- AGENTS.md dincharya/reminders.py tests/test_reminder_worker.py docs/HANDOFF.md docs/ROADMAP.md docs/ARCHITECTURE.md docs/DECISIONS.md docs/DEVELOPMENT_POLICY.md docs/MILESTONE2_PLAN.md
git commit -m "fix: harden reminder acknowledgement recovery and plan Milestone 2"
```

Do not repeat live Telegram acceptance. No production credentials/services,
private inputs, Docker tests, deployment or merge used for this planning task.
The prior sanitized [acceptance report](PR1_FOCUSED_ACCEPTANCE_RESULTS.md) and
[review](PR1_PREMERGE_REVIEW.md) remain historical evidence, not pending PR gates.
Next branch task after reviewing/recording this change: 2D legacy decision and
managed-series coexistence tests, then targeted 2E recovery/receipt work. The
missing exact provenance manifest and Panchang policy remain later owner gates.

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

