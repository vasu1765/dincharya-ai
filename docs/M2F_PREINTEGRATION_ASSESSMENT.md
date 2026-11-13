# Milestone 2F — bounded personal recurrence pre-integration assessment

Pushed base `34b6270901d0d09ba0d96e445185277cc2090f4d`, branch
`development/m2f-skyfield-feasibility`. Entry clean, HEAD/tracking/GitHub agreed;
no open PR. Owner accepts the previous checkpoint as offline research only.
This assessment adds no integration and grants no scheduling/engine approval.
AGENTS.md already expresses the required boundaries; no instruction change needed.

## Readiness decision

**Ready to propose a narrowly scoped isolated contract test, after owner approval.**
Not ready for persistent or live lunar scheduling. The finite reference panel and
pure preview contracts are adequate for that proposed test; this is not a claim
that every historical/future calendar case is validated. No open-ended astronomy
investigation is required to review the next-step proposal.

| Component | Classification | Evidence / practical limit |
| --- | --- | --- |
| Bounded personal rule parsing and preview | Ready for isolated integration testing | Explicit rule/birth/convention/intercalation/repetition choices, pure local calculation; no service or fixture lookup by evaluator. Trusted generated inputs only; no production API/auth decoder. |
| Calendar occurrence key arithmetic | Ready for isolated integration testing | v2 key excludes calculation/date/policy; 2,487 cycle centers across1900–2100 checked with +/-8h shifts;50 actual new moons in1900/1950/2050/2100 checked for unique consecutive cycles. This is identity arithmetic, not all-year calendar accuracy. |
| Purnimanta ordinary/Adhika identity | Ready for isolated integration testing, selected2023 scope | Split ordinary Shravana halves share a canonical cycle; Adhika has its own; Amanta/Purnimanta distinctions retained. Other exceptional patterns need validation. |
| Ordinary personal date panel | Ready for isolated integration testing, finite cases | Published repeat/skip/date evidence and stated PAC boundary checked against actual computed Delhi sunrise under both hypotheses; no central-station substitution. |
| General calendar-date correctness | Requires additional validation | Uneven direct Purnimanta coverage, matching horizon/location conventions, wider exceptional cases. Previous all12-name selected coverage is retained, not rerun. |
| Astronomical accuracy | Requires additional validation | Original60-second timing diagnostics remain failed where recorded. No minute-level investigation or tolerance change in this checkpoint. Date agreement does not erase timing disagreement. |
| Preview comparison / change detection | Ready for isolated integration testing on research payloads | Reject duplicates, lost/new/renamed identity sets and application-state payloads; withhold date or policy changes; inputs untouched. Not an approved-occurrence editor. |
| Performance / cache behavior | Ready for isolated integration testing on development host | Bounded caches, network-free;1.963s with cold month cache,0.104ms warm identical call; shared sunrise cache may already be warm. No VPS/SLA certification. |
| User-specific event/series identity and v1 mapping | Requires additional validation and owner decision | Calendar key alone cannot distinguish two people/events. Future immutable series/event ID and one-to-one legacy mapping must scope the calendar key; no migration designed into SQL. |
| Persisted approval, observation versions, leases and history safety | Unsupported and must remain disabled | No lunar persistence adapter or transaction/approval integration tested. Existing Gregorian/reminder safeguards unchanged, not certified for lunar integration. |
| Delivery/resend and live scheduling | Unsupported and must remain disabled | No Telegram/worker integration; preview comparator cannot access a delivery ledger or transport. This is not an end-to-end no-resend proof. |
| Kshaya, ambiguous context and unselected dates | Unsupported and must remain disabled | Kshaya/multiple-ingress and uncertain cases produce no confidently selected date or reject; no guessed fallback. |
| Festival calculations / era-year conversion / other geography | Unsupported and must remain disabled | Personal sunrise recurrence is not an observance algorithm; no sampradaya inferred. Gregorian search year is not an era year. |

## Independent inspection of correctness and identity

Reviewed lunation_cycle(), _label(), preview(), logical_key() and
reconcile_calculations() directly, not just prior test summaries.

- Fixed epoch/spacing counts a canonical lunation; it never computes astronomy.
  The3-day residual guard prevents a near-half-cycle ambiguity from being assigned
  a key. Analytical center tests cover the entire supported range; physical
  new-moon tests are representative, not an exhaustive ephemeris validation.
- _label uses a backing Amanta lunation and, for ordinary Purnimanta Krishna,
  the following ordinary named lunation, skipping a matching Adhika when required.
  Canonical cycle distinguishes ordinary/Adhika even when names coincide. Existing
  unsupported-ingress/boundary paths remain fail-closed.
- preview enumerates a bounded half-open Gregorian civil window, retaining whole
  tithi intervals and all sunrise candidates before selection/clipping. One row
  per logical key is enforced. Overlapping requests may legitimately return the
  same key; a future adapter must deduplicate within the immutable user series.
  It must not globally deduplicate two birthdays/anniversaries sharing a calendar
  key, or append every recalculated row as a new event.
- logical_key strictly validates v2 fields. Different conventions/rules can have
  different calendar keys on the same civil day. Engine changes that alter names,
  cycles or the set of occurrences require reconciliation, never guessed matching.
- Comparison requires equivalent frozen query/series context. If a new engine
  moves an occurrence outside that window, the set mismatch rejects; it cannot
  silently delete the old occurrence. Duplicate, new or renamed keys likewise
  reject. Changed civil dates keep the identity but are withheld.

### Demonstrated comparison defects corrected

1. The helper accepted unknown prior approval/delivery/series fields and silently
   discarded them. Four red subcases reproduced this before the fix. It now
   accepts only the exact unapproved research-preview envelope/row shapes and
   research statuses; application records, approved/sent/uncertain markers and
   unexpected nested state reject. Scheduling=true or adopted-gate claims reject.
2. A changed birth_basis or repeated policy could silently pass if the selected
   date happened to be unchanged. A red test reproduced this. Comparison now
   retains the logical key but withholds selection as recurrence_policy_disagreement.
   Date-only changes remain calculation_date_disagreement. No input is mutated.

This protects the research boundary; it is **not authorization**, stored
reconciliation, approval-snapshot validation or receipt preservation. Approved
occurrences/delivered reminders are not accepted as comparison inputs. There is
no database or transport capability to change/send them here. A future adapter
must bind approved immutable rule/profile snapshots, observation versions, series
scope and sent/uncertain history, and prove those transaction boundaries separately.

## Personal recurrence policy contract

The same explicit calendar rule can represent a birthday or wedding anniversary.
Their user event/series IDs must differ even if their calendar keys match. No
purpose-based religious rule, marriage custom or festival policy is inferred.

| Choice / outcome | Tested or required behavior |
| --- | --- |
| Annual request | Enumerate the full stated Gregorian search year; preserve zero/one/multiple matches, not exactly-one by assumption. User must confirm interpretation before any future save. |
| Instant-of-birth | Use the supplied aware instant for paksha/tithi/month interpretation. No assumed noon. |
| Sunrise-tithi interpretation | Use Delhi sunrise on that civil date; retain basis in the rule. Synthetic April3,2023 10:00IST gives Shukla13 instant versus Shukla12 at sunrise. |
| Anniversary input with no event time | Require an explicit lunar rule or an explicit sunrise interpretation; do not invent an instant. Future natural-language confirmation is not implemented. |
| Future date assignment | Sunrise-based in both birth interpretations; choosing instant birth does not schedule future reminders at the birth time. Reminder time/lead-time integration is absent. |
| Repeated tithi | Default review/no date; explicit first or last picks one. Published April2/3,2023 Chaitra12 panel retained; identity independent of first/last policy. |
| Skipped tithi | Review/no date for every repetition policy; no previous/next-day fallback. Published Delhi April11/12,2023 skips Krishna6. |
| Ordinary only | In2023 Shravana Shukla9 selects August25, not Adhika July27. |
| Adhika only | In2023 selects July27. In2024 no matching Adhika occurrence; return empty, no fallback to ordinary and no automatic saved reminder. |
| Both | In2023 preserves both July27 and August25 with distinct ordinary/Adhika keys; not a duplicate. In a year without matching Adhika it yields only the ordinary result. |
| Changed interpretation/policy | Withhold for explicit review even if the date happens to remain the same; no silent update of a previously approved rule. |
| No confident selected date | Return needs_review with no selected date, or reject unsupported/range/context. An empty experimental result is not a certified statement about observance/ritual obligation. |

Explicit choices are supported research behavior, not approved defaults for
production. In particular, whether an Adhika birthday should use ordinary, Adhika
or both is the owner's rule choice; never infer a religious affiliation.

## Finite calendar-date acceptance panel

No new web crawl, publication download, ephemeris or dependency. Reused these
accepted public fixtures and their exact metadata; evaluator still reads none:

- [calendar-references.json](../prototypes/panchang/calendar-references.json):
  pinned Drik Delhi2023 PDF page8 repeat/skip facts; pages14/16 ordinary/Adhika
  daily tithis. Exact publisher coordinates differ from prototype; parsed reading
  is not visual certification. Month-context inference remains distinguished.
- [month-references.json](../prototypes/panchang/month-references.json):
  PAC1945SE pages55/60 support July27 Adhika and August25 ordinary Shravana9.
- [coverage-references.json](../prototypes/panchang/coverage-references.json):
  PAC1946SE page32 May1,2024 Saptami end05:47IST deliberately compared against
  computed Delhi dawn under both pinned hypotheses:403.895/389.546s separation,
  both choose May1. PAC central-station sunrise is not Delhi sunrise.
- Existing selected2023 Purnimanta/Amanta/Adhika boundaries and1983 multiple-ingress
  rejection exercised. Kshaya gets no new historical name or substitute date.

A synthetic dawn240s from a real tithi transition is withheld even with first
policy. A changed selected date between calculation profiles is also withheld.
These cover actual date-sensitive cases and error paths without restarting the
old minute-level Drik/Himalayan investigation. Original60-second diagnostic
results are byte-preserved and still failed where recorded. Publisher/model
metadata mismatches are not automatically labelled calculation defects. The
300s guard is conservative, not a proven universal physical-error bound.

### What passes, what does not

Selected panel/policy/identity checks pass; general calendar adoption does not.
Direct Purnimanta evidence remains uneven, exact publisher horizon/location
matching is incomplete and broad exceptions are unvalidated. These are bounded
acceptance limitations for an isolated pilot, not permission to guess dates or
restart an unlimited research program. Owner review should choose whether this
finite scope is acceptable for the next synthetic contract test.

## Focused results and repeatability

New [test_preintegration.py](../tests/panchang/test_preintegration.py) contains10
bounded assessment tests. Initial run:9 new +2 materially affected comparison
regressions =11 passes in14.017s. After adding the same-date policy correction,
that new test plus the2 comparison regressions passed in4.262s. **12 distinct
focused tests verified**, not a full unrelated regression run. Red evidence:
4 application-state subcases,1 same-date policy case before fixes.

[preintegration-results.json](../prototypes/panchang/preintegration-results.json)
records public/synthetic evidence and SHA256 of10 unchanged accepted fixture/result
files. No raw user data, secrets, backup artifacts or service state. Date/month
calculations, logical identity contract, pinned kernel/dependencies and cache bounds
are unchanged by the comparison fixes. No need to rerun all-month accuracy,
coordinate experiments or unrelated2C/2D/2E/n8n/live tests.

Performance check:1.963s with cold month cache;0.104ms identical warm result and
zero additional month calculations. Shared astronomy sunrise cache may already
be warm, so this is not a fresh-process cold benchmark. Month32/preview8/sunrise800
bounds remain. Development host only; retain prior pinned-environment evidence.

Reproduce from the repo root with the existing isolated Python environment:

```bash
DINCHARYA_PUBLIC_DE440S=/EXTERNAL/PUBLIC/de440s.bsp \
  OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /tmp/dincharya-panchang-repro/bin/python -B -m unittest discover \
  -s tests/panchang -p test_preintegration.py -v
```

The two affected old regression names are documented in the recorded run:
test_logical_identity_ignores_profile_date_and_policy and
test_duplicate_and_legacy_cycle_changes_require_review in test_coverage.py.

## Smallest recommended next step — requires approval, NOT implemented

Approve one **isolated in-memory contract-adapter dry run** for a fixed synthetic
birthday and wedding series. Feed preview output into a fake proposal/approval
interface and fake ledger; accept no database credentials or live transport.
Test explicit approval before materialization, immutable series ID + calendar-key
composition, same-key recalculation, changed date/policy rejection, overlapping
windows, duplicate submissions and fake sent/uncertain history remaining untouched.
Only propose rows; no worker delivery, scheduling, n8n or migration.

This would test the first integration seam without changing storage architecture.
It would not certify PostgreSQL transactions, actual reminder leases or deployment.
Those remain separately approved future stages. **Do not implement this adapter
or begin persistent mapping from this assessment alone.** No owner decision is
needed to complete this report; next-step scope/identity/adoption policy requires
explicit approval. Neutral profile/future consolidated labelled Smarta/Vaishnava
design and existing n8n/PostgreSQL safeguards remain intact.
