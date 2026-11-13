# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint — 2F lunar-month research, stop for review

Branch `development/m2f-skyfield-feasibility`; pushed base
`452bbcd28653ae8a8530ada57c3e0bd33e2f2d6b`. Entry tree clean; HEAD/tracking agree,
GitHub confirmed the commit. Previous 6f1f0b7-based uncommitted instructions are
superseded. Owner/ChatGPT accepted prior validation for **continued research only**.
Git metadata remains mounted read-only; no stage/commit/bypass attempted. Preserve
current local additions. Source and previous evidence bytes are unchanged.

- New separate MonthResearch candidate/annual-example layer; approved/general
  month_label and annual_preview remain Unsupported. No scheduling adoption.
- **21 Amanta selected dates match** across 2023/2024/early2025 (seven names).
  **18 Purnimanta comparisons match**, but only seven have direct publisher-label
  corroboration; eleven are calendar-context deductions. Not a general validation.
- Adhika Shravana keeps its name/flag in both pakshas. Ordinary Krishna before it
  uses Shravana ordinary, with the ordinary Shukla half after Adhika. No false
  contiguous Purnimanta month bounds. Kshaya/multiple-ingress 1983 period rejects.
- **Nine new PAC boundaries within unchanged 60 s**, max residual 24.829 s.
  Original Drik/Himalayan timing failures remain unchanged/unexplained; no new
  distinguishing evidence warranted repeating old coordinate experiments.
- **15 explicit experimental previews** match evidence, including repeated once,
  skipped withheld, ordinary/Adhika separation, Krishna conversion and multi-year
  Shukla examples. Unknown rule/year rejects. These are bounded attested examples,
  not complete annual enumeration. Delhi sunrise remains experimental.
- Three year-anchor checks match Chaitra Shukla transition. This token is the
  Gregorian year of that new moon, not Vikrama/Shaka/regional era conversion.
- Nine distinct new tests verified: initial eight passed 36.669 s; final three
  affected/new cases passed 41.061 s. No unrelated 2C/2D/2E or accepted coordinate,
  Docker/n8n/live suites repeated. Previous source/tests/tolerances retained.
- Offline evidence runner exit2 with usable_for_scheduling=false; 40.546 s wall,
  peak RSS 56,008 KiB under 512 MiB/60 CPU-second limits. Back-search is expensive;
  no VPS capacity claim. Pinned environment/kernel reused; no dependency changes.
- Public IMD 2024–25 ZIP and Drik Delhi2023 PDF acquired outside Git; source hashes,
  editions, precise pages, coordinate differences and parsing/context limitations
  documented. No bulk scraper; Delhi2024 PDF404 is recorded, no substitute.

See [report/matrix](M2F_FEASIBILITY_RESULTS.md),
[fixtures](../prototypes/panchang/month-references.json) and
[recorded results](../prototypes/panchang/month-results.json). Old references.json,
research-references.json, feasibility-results.json and validation-results.json are
byte-preserved. Source-safety/AST/JSON/local-link/diff checks and issue #2 updated.

Stop for ChatGPT review. Remaining: other five month names, multi-year/direct
Purnimanta goldens and other intercalations, independent precise Lahiri epochs,
matched sunrise, unresolved timing, Kshaya/era/general annual behavior. No engine
adoption, persistent schedules, migrations, n8n change, festival rules, Telegram,
private backup/2B search, production, deployment or main merge. Neutral religious
profile, future consolidated labelled Smarta/Vaishnava design and all PostgreSQL
approval/identity/lease/receipt/audit safeguards unchanged. All Milestone 2 first.

Run in normal WSL, confirming the branch above. Only these 12 explicit safe files
belong in this checkpoint; review the index before committing/pushing:

```bash
git branch --show-current
git status --short
git diff --check
git add -- \
  prototypes/panchang/month_research.py \
  prototypes/panchang/month_validation.py \
  prototypes/panchang/month-references.json \
  prototypes/panchang/month-results.json \
  tests/panchang/test_month_research.py \
  prototypes/panchang/README.md \
  docs/M2F_FEASIBILITY_RESULTS.md \
  docs/M2F_PANCHANG_DESIGN.md \
  docs/MILESTONE2_PLAN.md \
  docs/ROADMAP.md \
  docs/DECISIONS.md \
  docs/HANDOFF.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "feat: add evidence-bounded lunar month research previews"
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

