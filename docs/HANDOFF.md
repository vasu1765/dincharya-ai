# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint

Branch `development/m2-recovery-acceptance`, pushed base `cb6fdd7` (full SHA
cb6fdd73686fbdb19b29aea1011585faf4205e46). Working tree was clean at entry;
HEAD and origin tracking ref matched, GitHub confirmed the commit, and no open
PR was found for this branch. The prior 2D checkpoint is committed/pushed; old
ff6198d/uncommitted references are superseded. PR #1 remains merged.

Owner authorized **Milestone 2F Phase 1 research/design only**. New
[M2F_PANCHANG_DESIGN.md](M2F_PANCHANG_DESIGN.md) records primary research sources,
confirmed facts versus recommendations/unresolved decisions, functional/calendar
requirements, engine/reference comparisons, stable occurrence/approval/reminder
integration, fixture criteria and phased implementation gates. No engine,
dependency, migration or n8n change has been implemented.

Recommendation pending approval: evaluate Skyfield with pinned local DE440s
first; keep astronomical tithi intervals, sunrise-based dates, personal recurrence
policies and festival observance profiles distinct. Delhi/Asia-Kolkata and
Purnimanta default/Amanta configuration reflect owner requirements; exact profile,
ayanamsa/sunrise and exceptional-date choices remain pending. Swiss Ephemeris is
an alternative with explicit license/binding-support review. PAC and Skyfield
sunrise models differ, so reference comparisons must bind coordinates/conventions.

Proposed personal defaults: first repeated sunrise once, skipped-tithi/Kshaya-month
cases require review, ordinary-month anniversaries unless explicitly selected,
adhika-origin rules clarified. Propose North-Indian Smarta as a candidate profile,
not an inferred owner tradition. Each requested observance needs independent
verification; tithi-only matching cannot silently schedule every festival.

Storage approval needed: current ledger allows one event/date delivery and due
at event time. Stable Hindu logical identity, independent notification due time,
bounded lead-aware lookahead and multiple slots require reviewed additive design.
Preferred candidate keeps old history/uniqueness and adds companion jobs for extra
slots with shared lease/receipt/quarantine semantics. This is a proposal only.

Stop for owner decisions before implementation: engine/licensing, Delhi/sunrise/
ayanamsa profile, personal exception policies, ritual authority/tradition and
staged identity/notification storage. See the numbered approval list in the design.
No choice is recorded as accepted merely because it is recommended.

Only documentation checks ran: explicit five-file safe-source scan, local-link
checks, whitespace and diff review. No Docker/SQL/Panchang runtime tests, package
installation, Telegram, n8n operation, private backup/manifest access, production,
deployment or merge. No runtime accuracy/performance or golden fixture is claimed.
Source and engine/data/reference license verification remain implementation gates.
GitHub issue #2 reflects the pushed 2D checkpoint and current design status.

2D synthetic database/API acceptance remains passed at cb6fdd7; full trusted
application/workflow adoption is blocked by 2B. The owner confirmed original
manifest path is unknown and authorizes no private searches, unknown artifacts,
manifest replacement or capture. Repository-only contract/test-gap/checklist work
can proceed later; this phase does not unblock provenance or private-source
adoption. Production reconciliation and all resend/reset operations stay disabled.
All Milestone 2, including Panchang and operations, precedes other orchestrators.

Git metadata is still mounted read-only; no Git write/bypass attempted. After
reviewing the design and index, use these exact five-safe-file commands in your
normal WSL terminal; committing documentation does not authorize implementation:

```bash
git status --short
git branch --show-current
git diff --check
git add -- \
  docs/M2F_PANCHANG_DESIGN.md \
  docs/HANDOFF.md \
  docs/MILESTONE2_PLAN.md \
  docs/DECISIONS.md \
  docs/ROADMAP.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "docs: propose Hindu Panchang scheduling design and approval gates"
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

