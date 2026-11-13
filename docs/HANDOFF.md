# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint — 2F focused validation, stop for review

Entry and current branch `development/m2f-skyfield-feasibility`; latest pushed
commit `6f1f0b72729023d84123891725fd0b018bc1c584`. Entry tree clean; HEAD/tracking
and GitHub agreed. No open PR found. This supersedes the old 9524757-base branch
creation instructions. Existing committed prototype is preserved; current changes
are uncommitted because Git metadata remains read-only. No write/bypass attempted.

Owner accepted prior prototype as research, **not engine adoption or scheduling**.
[Validation report](M2F_FEASIBILITY_RESULTS.md) and
[recorded numeric evidence](../prototypes/panchang/validation-results.json) are current.
Original references.json and feasibility-results.json remain unchanged.

- **PASS scoped regressions:** 23 tests, final run 4.531 s. Fixed modulo/wrap,
  indistinguishable sample motion, numerical endpoint/interval ambiguity,
  unsupported padded interval exposure, lower/upper preview edges and sanitized
  bad sunrise-model rejection. Exact/near transitions and 1900/2100 exercised.
- **FAIL original accuracy:** +85.886/+75.668 s Drik deltas reproduced. Nine
  apparent/astrometric/geometric and true-date/mean-date/J2000 experiments do not
  explain them. Original 60-second gate unchanged; no fixture replacement.
- **Mixed new public evidence:** USNO 1/1 and IMD PAC 3/3 within 60 s; Himalayan
  Academy 1/2, another -154.138 s mismatch. Metadata/extraction limits recorded.
- Explicit ERFA-based Lahiri candidate: selected three vendor epoch reproductions
  within 0.002 arcsecond, four independent PAC ingresses within 27 seconds and
  three selected Amanta cases (ordinary Chaitra, Adhika/ordinary Shravana) agree.
  This is limited research, not general month validation. Public month names,
  Purnimanta conversion, Kshaya and annual birthdays/anniversaries remain disabled.
- Added hash-locked pyerfa 2.0.1.5 (ERFA 2.0.1, SOFA 20231011) in isolated /tmp
  environment. No Swiss implementation installed/copied. Public PAC PDF extracted
  with research-only pypdf 6.1.1 outside Git; archive/PDF hashes and exact pages
  recorded. No raw publication, kernel or wheel added to the repository.
- New offline validation CLI exits 2, usable_for_scheduling=false; 2.254 s wall,
  peak RSS 56,792 KiB on development host under 512 MiB/60 CPU-second limits.
  Runtime has no network fallback; Python audit guards are not an OS sandbox.
- Only affected prototype tests/research/checks ran. No unrelated 2C/2D/2E,
  reconciliation, Docker/n8n/live acceptance; no DB migration, Telegram operation,
  private backup/2B search, production access, deployment or main merge.

Next gates: explain independent timing failures; obtain matched Delhi sunrise
metadata, precise independent Lahiri epoch data and multi-year Amanta/exception
fixtures; separately validate Purnimanta names. Stop after this checkpoint for
ChatGPT review; no persistent integration or festival implementation. n8n and
PostgreSQL approvals/identity/lease/receipt/audit safeguards remain unchanged.
Religiously neutral user profile and consolidated labelled future Smarta/Vaishnava
reminders remain intended behavior. 2B manifest remains unknown/unauthorized;
no search or substitute. Complete all Milestone 2 before any other orchestrator.
GitHub issue #2 is updated with this checkpoint; implementation remains local
until the owner runs these commands in normal WSL. Inspect staged changes before
committing; only the following 16 explicit safe files belong in this commit.

```bash
git status --short
git branch --show-current
git diff --check
git add -- \
  prototypes/panchang/astronomy.py \
  prototypes/panchang/investigation.py \
  prototypes/panchang/validation.py \
  prototypes/panchang/requirements.txt \
  prototypes/panchang/ephemeris.json \
  prototypes/panchang/research-references.json \
  prototypes/panchang/validation-results.json \
  prototypes/panchang/README.md \
  tests/panchang/test_astronomy.py \
  tests/panchang/test_validation.py \
  tests/panchang/test_investigation.py \
  docs/M2F_FEASIBILITY_RESULTS.md \
  docs/M2F_PANCHANG_DESIGN.md \
  docs/MILESTONE2_PLAN.md \
  docs/ROADMAP.md \
  docs/HANDOFF.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "test: investigate Panchang timing and harden boundary validation"
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

