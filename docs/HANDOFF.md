# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint

Branch `development/m2-recovery-acceptance`, pushed base `ff6198d` (restart/outage
checkpoint). Working tree was clean at entry; local HEAD and origin tracking SHA
matched and GitHub confirmed the commit. Issue #2 now records restart/outage as
pushed and the current 2D results; no open PR was found for this branch. PR #1 remains merged.

Outstanding 2D synthetic recurrence/API acceptance now passed. Two new SQL cases
cover weekly/yearly intervals and December–January transitions, combined selectors,
inclusive start/until and beyond-until exclusion, invalid concrete dates/ranges,
leap/century behavior, and approved series edits over existing exceptions,
cancellations and future reminder rows. Deliberate series conflict rejects until
explicit owner force approval; unauthorized force and stale decisions reject.
Event/rule/ledger identities, unaffected override output and full sent/uncertain
history remain stable; dormant explicit cancellations survive rule changes.
No application defect was demonstrated; no migration or application change.

Both new SQL cases passed; only the strengthened calendar case was rerun.
Three affected runner preflight tests passed. Existing 2C/2E/reconciliation/n8n/
live Telegram suites were not rerun. See [2D matrix/evidence](M2D_RECURRENCE_ACCEPTANCE.md)
for passed cases, design limits and the 2B integration block. The new series test
uses reminder APIs only to verify the effects of its newly tested rule changes.
Restart/outage evidence remains at [prior checkpoint](M2_RESTART_RECOVERY_RESULTS.md).

Pinned daemon/image, exact schema-only input unchanged, no-network/tmpfs/read-only
isolation, teardown and unchanged existing running container IDs were verified.
Host HBA SCRAM/local-only trust, restricted worker access, disabled reconciliation
and empty audit were checked. Credential/logging, executor roles and immutable
audit code remain unchanged. Source-safety, changed Python AST and whitespace/diff
checks passed. No production/private-directory access, Telegram sends, resend/
reset, deployment or merge. All Milestone 2 including Hindu Panchang precedes
other orchestrators; production reconciliation remains disabled.

Full 2D application/workflow closure remains blocked by reviewed 2B adoption.
The owner confirmed the original manifest path is not yet known and did not
authorize private searches or referenced-artifact access. Provenance is blocked
until the **exact original manifest path and explicit file-only authorization**
are supplied; no search or manifest read was performed. Do not open referenced/adjacent artifacts
without exact authorization or recreate/substitute a manifest without approval.
Repository-only follow-up can map validator formats, audit synthetic-test gaps
and refine the adoption checklist; it cannot establish original provenance.
Details and follow-up validation boundaries are in the 2D report. Panchang source/tradition/reference,
production operator evidence/identity, and 2G operations remain separate gates.

Git metadata remains mounted read-only; no Git write/bypass attempted. Review the
new untracked SQL/report as well as tracked diff, verify branch/index, then run
these exact eight-safe-file commit commands in your normal WSL terminal:

```bash
git status --short
git branch --show-current
git diff --check
git add -- \
  tests/sql/gregorian_calendar_acceptance.sql \
  tests/sql/gregorian_series_acceptance.sql \
  tests/integration/focused_application_runner.py \
  tests/sql/README.md \
  docs/M2D_RECURRENCE_ACCEPTANCE.md \
  docs/HANDOFF.md \
  docs/MILESTONE2_PLAN.md \
  docs/ROADMAP.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "test: complete Gregorian recurrence API acceptance matrix"
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

