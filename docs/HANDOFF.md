# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint — all-name coverage / identity v2, stop offline for review

Branch development/m2f-skyfield-feasibility, pushed base
`0a1cae678dc9a00a120a56a703f74a23935bfde2`; entry clean, HEAD/tracking/GitHub
agree, no open PR. Earlier uncommitted2bd37c0-base instructions are superseded
by this pushed base. Current local work remains uncommitted; Git metadata read-only,
no bypass/stage/commit. No scheduling adoption.

- All12 names selected research support:47 direct PAC Amanta name/paksha/tithi
  cases across1945SE/1946SE editions,47 inferred Purnimanta comparisons and5 new
  direct Purnimanta corroborations. No PAC station/solar-heading/Delhi confusion.
  Direct Purnimanta coverage remains uneven; not full calendar certification.
- New logical identityv2 excludes profile/date/policy. Fixed guarded lunation
  cycle anchors canonical ordinary/Adhika month occurrences. Provenance and
  selected-date policy separate. Profile changes retain key; offline comparison
  withholds changed dates, rejects duplicate/legacy/changed identity sets.
- Future persisted v1-to-v2 mapping, per-series scope, changed labels/cycles/date
  reconciliation need explicit owner approval; no migration or stored change.
- Confirmed source defect fixed: preview used120s despite documented300s guard.
  It now actually withholds240s synthetic sunrise even with explicit first policy.
  Pinned model, old astronomy guards and60s diagnostics unchanged.
- Deliberate near-sunrise PAC May1,2024 boundary05:47IST vs computed Delhi dawn
  gives403.895/389.546s margin, same Saptami/date under both hypotheses. This is
  not a direct matching-profile Delhi sunrise publication. Date-changing
  disagreements require investigation/withholding even beyond a heuristic guard.
- Seven new focused tests verified plus12 affected existing recurrence tests
  (22.265s). New strengthened guard/cycle cases rerun. All8 old fixture/result
  bytes preserved. No unrelated integration/old coordinate experiments repeated.
- Offline report exits2, not adoption. Cold annual1.991s vs recorded2.056s,
  warm0.089ms, month32/preview8/sunrise800 bounds, peak RSS87,424KiB. Same pinned
  local packages/kernel; no new download/dependency. Public archived PAC files
  reused outside Git; finite selected primary web labels, no bulk scraper.

See [full coverage matrix / contract / proposed gate](M2F_MONTH_COVERAGE.md),
[preview design](M2F_RECURRENCE_PREVIEW.md),
[results](../prototypes/panchang/coverage-results.json) and
[fixtures](../prototypes/panchang/coverage-references.json). Source-safety,
AST/JSON/link/diff and evidence checks passed; issue2 updated.

Remaining: direct Purnimanta and multi-year exception/reference-profile coverage,
Kshaya/ambiguous boundaries and identity mapping (withheld), independent precise
Lahiri epochs and original timing failures.60-second timing diagnostic remains
failed, separate from selected date checks. Overall date gate is proposed and
incomplete; adoption/persistence policy requires owner review. Neutral profile,
future consolidated Smarta/Vaishnava design and n8n/PostgreSQL safeguards remain.
No production/private backups/2B search, migration, n8n/Telegram, festivals,
deployment/main merge or other orchestrator. Stop after offline checkpoint.

Normal WSL commands: confirm branch, inspect index; only these16 safe files:

```bash
git branch --show-current
git status --short
git diff --check
git add -- \
  prototypes/panchang/recurrence.py \
  prototypes/panchang/coverage_validation.py \
  prototypes/panchang/coverage-references.json \
  prototypes/panchang/coverage-results.json \
  tests/panchang/test_recurrence.py \
  tests/panchang/test_coverage.py \
  docs/M2F_MONTH_COVERAGE.md \
  docs/M2F_RECURRENCE_PREVIEW.md \
  docs/M2F_FEASIBILITY_RESULTS.md \
  docs/HANDOFF.md \
  docs/M2F_PANCHANG_DESIGN.md \
  docs/MILESTONE2_PLAN.md \
  docs/ROADMAP.md \
  docs/DECISIONS.md \
  docs/ARCHITECTURE.md \
  prototypes/panchang/README.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "feat: validate all lunar names and separate logical occurrence identity"
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

