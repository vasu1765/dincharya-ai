# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint — bounded pre-integration assessment, stop for approval

Branch development/m2f-skyfield-feasibility, pushed base
`34b6270901d0d09ba0d96e445185277cc2090f4d`. Entry clean; HEAD/tracking/GitHub
agree, no open PR. Prior uncommitted0a1cae6-base instructions are superseded.
Git remains read-only; no stage/commit/bypass. Current local assessment ready for
review, NOT engine adoption or permission to integrate.

- Independently inspected lunation_cycle/_label/preview/logical_key/comparison.
  Calendar key is not a user series/event ID.2,487 analytic centers with+/-8h
  shifts and50 actual new moons at1900/1950/2050/2100 preserve identity arithmetic;
  this does not certify all-year calendar accuracy.
- Fixed two demonstrated comparator gaps: approval/delivery/series fields could
  be silently discarded; changed birth/repetition policy could pass on same date.
  Strict research-only shapes/statuses now reject application payloads; changed
  policy/date retains key but withholds date. No ledger/transport or stored action.
- Bounded accepted reference panel covers actual near-Delhi sunrise, repeated/
  skipped dates, ordinary/Adhika choices, Purnimanta split halves and Kshaya
  rejection. Existing public source limitations remain. No new astronomy research,
  new download or minute-level discrepancy rerun;60s diagnostics unchanged.
- Personal birthday/anniversary policy explicit: instant versus sunrise input,
  sunrise future assignment, repeated first/last/review, skipped review, ordinary/
  Adhika/both choices including no-Adhika years. No fallback date or festival rule.
-12 distinct focused tests verified: initial11 in14.017s; new same-date policy
  plus2 affected regressions in4.262s. Red-before-fix evidence recorded. Existing10
  fixture/result files preserved. No unrelated integration suite repeated.
- Performance:1.963s cold month cache /0.104ms warm, no extra month calculations;
  shared sunrise cache may be warm. Bounds unchanged; not a VPS certification.

[Readiness matrix / policy / next-step proposal](M2F_PREINTEGRATION_ASSESSMENT.md)
is authoritative for this checkpoint. Pure preview/identity/change detection ready
for a proposed isolated contract test; general astronomy/calendar validation still
limited; persistence/approval/delivery safety unsupported and disabled. Cannot
claim preservation of stored sent/uncertain records without a future adapter test.
AGENTS unchanged because existing boundaries suffice. Source-safety/AST/JSON/link/
diff/evidence checks passed; GitHub issue2 updated.

Next step recommended only: owner-approved in-memory fake proposal/approval/ledger
adapter dry run for two synthetic personal series, no transport/database. NOT
implemented. Owner must approve scope before integration, persisted v1 mapping,
series identity or engine/date-policy adoption. All current outputs research-only.
No production/private backup/2B access, migration, n8n/Telegram, live scheduling,
festival implementation, deployment, main merge or other orchestrator. Neutral
profile and future consolidated Smarta/Vaishnava design preserved. Stop here.

Normal WSL commands, confirming branch and reviewing index;13 explicit safe files:

```bash
git branch --show-current
git status --short
git diff --check
git add -- \
  prototypes/panchang/recurrence.py \
  prototypes/panchang/preintegration-results.json \
  tests/panchang/test_preintegration.py \
  docs/M2F_PREINTEGRATION_ASSESSMENT.md \
  docs/M2F_RECURRENCE_PREVIEW.md \
  docs/M2F_FEASIBILITY_RESULTS.md \
  docs/HANDOFF.md \
  docs/MILESTONE2_PLAN.md \
  docs/ROADMAP.md \
  docs/DECISIONS.md \
  docs/ARCHITECTURE.md \
  docs/M2F_PANCHANG_DESIGN.md \
  prototypes/panchang/README.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "fix: bound lunar preview comparison and assess integration readiness"
git push origin development/m2f-skyfield-feasibility
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

