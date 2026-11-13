# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint

Entry branch `development/m2-recovery-acceptance`, pushed base `9524757` (full SHA
952475720e1990f635eed7f1710b123018262db0). Working tree was clean; HEAD and origin
tracking ref agreed and GitHub confirmed the commit. No open PR found. Earlier
cb6fdd7-based/uncommitted design instructions are superseded. PR #1 is merged.

Owner D14 authorized an isolated offline Skyfield/DE440s feasibility prototype,
not final adoption, festivals, persistent scheduling or reminder integration.
[Prototype README](../prototypes/panchang/README.md) gives exact reproduction;
[results](M2F_FEASIBILITY_RESULTS.md) distinguish scoped tests from accuracy gates.

Implemented: pinned local astronomy dependencies/data, geocentric elongation and
all tithi transitions, instant/sunrise distinction, two labelled Delhi sunrise
hypotheses, physical Amanta/Purnimanta boundaries and generic monthly previews.
Repeated sunrise chooses first once; skipped/near-boundary cases need review.
Known 2023 intercalary period has zero ingress under three constant-offset
sensitivity hypotheses, explicitly not exact Lahiri or a month-naming engine.

**Incomplete for scheduling:** 11 focused tests passed, NASA phase differences
within provisional 60 seconds, but two Drik tithi endpoints differ by about
86/76 seconds, outside the unchanged threshold. Sunrise is numerically close to
one rounded reference but exact coordinate/model metadata is unconfirmed; USNO
lookup failed DNS. Exact Lahiri, named-month/intercalary conversion and annual
birthday/anniversary output are unsupported and fail closed. Do not widen tests,
guess names or treat physical month bounds as verified calendar label conversion.
CLI deliberately exits 2 with usable_for_scheduling=false. No engine adopted.

Measured: 371 transitions for 2026 in 0.305 seconds; complete experiment after
imports 1.154 seconds wall, peak RSS 75.14 MiB under 512 MiB address-space/60 CPU
second limits. Development Linux host only, not VPS capacity or physical timing
accuracy. Exact dependency/kernel/timezone/timescale hashes and observed metrics
are recorded in source metadata and the sanitized public result JSON.

Dependencies/kernel were acquired from public PyPI/JPL into a separate /tmp venv;
no application environment or package credentials used. Runtime has explicit
local-only file loading, no network fallback and Python socket audit guards
(not an OS network namespace). New assets/fixtures are public numeric facts or
invented data; BSP/wheels remain outside Git. No Docker/DB/n8n/Telegram/production,
private backup/2B search, migration, deployment, merge or unrelated suite ran.
Only 11 new focused tests, explicit safe-source/AST/JSON/local-link/whitespace/diff
checks. Existing services and lease/receipt/audit infrastructure are untouched.

Owner religious profile is **neutral**. Future supported festivals should show
labelled Smarta/Vaishnava dates in one consolidated reminder when different;
shared dates deduplicate. Proposed named reference pair: Drik New Delhi Smartha
and ISKCON/Gaudiya GBC Calendar Committee GCal 11. Export/build/settings verification
is still pending; no festival rule implemented or owner sampradaya assigned.

Stop at isolated feasibility. Next review: resolve tithi reference discrepancies,
obtain matched Delhi sunrise evidence and validate one exact Lahiri convention
before month names/annual rules. Persistent identity/slot storage and delivery
integration require further review; n8n stays. 2B provenance remains blocked;
no search/replacement/capture. All Milestone 2 including Panchang/operations
precedes other orchestrators. Production reconciliation/resend/reset remain disabled.
GitHub issue #2 is updated with scope, outcomes, limitations and the neutral profile.

Git metadata is mounted read-only; no write/bypass attempted. A separate branch
is practical from your normal WSL terminal, carrying this working tree forward.
Review only these 15 safe files and the index; no binaries, /tmp files or private
inputs belong in the commit. Commands below do not push, deploy or merge:

```bash
git status --short
git switch -c development/m2f-skyfield-feasibility
git diff --check
git add -- \
  .gitignore \
  prototypes/panchang/astronomy.py \
  prototypes/panchang/feasibility.py \
  prototypes/panchang/requirements.txt \
  prototypes/panchang/ephemeris.json \
  prototypes/panchang/references.json \
  prototypes/panchang/feasibility-results.json \
  prototypes/panchang/README.md \
  tests/panchang/test_astronomy.py \
  docs/M2F_FEASIBILITY_RESULTS.md \
  docs/M2F_PANCHANG_DESIGN.md \
  docs/HANDOFF.md \
  docs/MILESTONE2_PLAN.md \
  docs/DECISIONS.md \
  docs/ROADMAP.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "feat: add isolated offline Panchang astronomy feasibility prototype"
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

