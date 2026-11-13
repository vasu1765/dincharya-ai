# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint — general offline personal lunar preview, stop for review

Branch `development/m2f-skyfield-feasibility`, pushed base
`2bd37c09c4a3e25d4dcc3d6e7476c0665ac46b77`. Entry tree clean; local HEAD/tracking
and GitHub agree; no open PR. Prior uncommitted/allowlist-only instructions are
superseded. Owner authorizes general offline research, NOT scheduling adoption.
Git remains read-only; no stage/commit/bypass. Preserve current local work.

- Added separate recurrence.py immutable rules, full Gregorian-year/monthly/custom
  window enumeration, explicit instant/sunrise birth derivation. No fixture lookup
  by evaluator. Old example API, original astronomy/model/tests remain unchanged.
- Structured research identity: profile/convention/month/ordinary-Adhika/canonical
  Shukla month-anchor UTC date/paksha/tithi. Ordinary Purnimanta Shravana halves
  around Adhika now share August16 anchor; Adhika uses July17. No DB adoption.
- Default repeated-date review; first/last must be explicit. Skipped/uncertain,
  Kshaya, unsupported month names/backing contexts have no selected date. Seven
  selected-research names; other five are withheld, not silently enabled.
- New conservative300s calendar-date guard leaves original0.1s/120s policies and
  60s timing diagnostic unchanged. Separate selected date gate passes11 reference
  rows/10 dates/22 model comparisons and six repeat/skip policy checks. Overall
  calendar adoption remains incomplete and usable_for_scheduling=false.
- New public2026 evidence distinguishes personal sunrise Navami on March27 from
  Smarta festival March26. Drik/Panchangam both agree on sunrise Navami but report
  transition10:06/10:07 and sunrise06:17/06:20 respectively. Model transition
  +82.480s/+22.494s means diagnostic fail/pass, not a proven calculation defect.
  Old Drik/Himalayan failures remain unexplained, unchanged and not rerun.
- Bounded LRU month32/preview8/owned sunrise800; exact containment, deep copies,
  fixed profile invalidation, no interpolation/model changes or persistent cache.
  Measured annual2.056s cold,0.000074s warm,zero new month calculations; complete
  report8.559s,peak RSS91,504KiB. Not a like-for-like old workload/VPS claim.
- 12 new focused tests passed18.563s; affected date/cold-identity/profile tests
  rerun after additions. New runner exit2, network guarded, same pinned environment.
  No new package/kernel. Six accepted evidence files byte-preserved.

See [design/API/gates](M2F_RECURRENCE_PREVIEW.md),
[current matrix](M2F_FEASIBILITY_RESULTS.md),
[fixtures](../prototypes/panchang/calendar-references.json) and
[results](../prototypes/panchang/recurrence-results.json). Explicit source-safety,
AST/JSON/link/diff and evidence checks passed; GitHub issue2 updated.

Stop after offline checkpoint for review. Remaining: five names and broader
multi-year/exception/calendar goldens, matched source sunrise profiles, unresolved
physical timing, independent precise Lahiri epochs and adoption/identity policy
review. Public general scheduling APIs remain disabled. No production/private
backup/2B search, DB migration, n8n/Telegram, festival implementation, deployment,
main merge or unrelated accepted integration tests. Neutral owner profile and
future consolidated labelled Smarta/Vaishnava design unchanged. All Milestone2
before another orchestrator. Existing authorization/lease/receipt/audit unchanged.

Normal WSL commands; confirm the branch above and inspect the index. Only these
13 explicit safe files belong to this checkpoint:

```bash
git branch --show-current
git status --short
git diff --check
git add -- \
  prototypes/panchang/recurrence.py \
  prototypes/panchang/recurrence_validation.py \
  prototypes/panchang/calendar-references.json \
  prototypes/panchang/recurrence-results.json \
  tests/panchang/test_recurrence.py \
  docs/M2F_RECURRENCE_PREVIEW.md \
  docs/M2F_FEASIBILITY_RESULTS.md \
  docs/HANDOFF.md \
  docs/M2F_PANCHANG_DESIGN.md \
  docs/MILESTONE2_PLAN.md \
  docs/ROADMAP.md \
  docs/DECISIONS.md \
  prototypes/panchang/README.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "feat: add general offline personal lunar recurrence previews"
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

