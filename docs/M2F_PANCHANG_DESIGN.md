# Current assessment gate

See [bounded pre-integration assessment](M2F_PREINTEGRATION_ASSESSMENT.md) from
pushed34b6270. Personal policies, identity invariants and finite reference-panel
results are explicit. The next isolated adapter test is proposed, not authorized
or implemented. General engine/persistence/delivery/festival adoption stays disabled.

# Milestone 2F — Hindu Panchang scheduling design

Status: **isolated Skyfield/DE440s feasibility authorized; final engine adoption,
festival rules and persistent integration are not authorized**. The Phase 1 design
was pushed at `952475720e1990f635eed7f1710b123018262db0`; the prototype is now
pushed at `6f1f0b7`; timing/range validation is pushed at `452bbcd` on
development/m2f-skyfield-feasibility. The current research entered clean there. See
[measured feasibility results](M2F_FEASIBILITY_RESULTS.md) for implemented scope,
failed reference comparisons, unsupported month/annual-rule paths and next gates.
Original recommendations below are historical proposals where superseded by the
owner decisions in the next section; do not infer approval for storage changes.

## Owner decisions governing the isolated feasibility

- Skyfield with pinned local DE440s is approved as an isolated prototype, not final
  engine adoption. Delhi/Asia-Kolkata and Purnimanta default/Amanta configuration
  remain; exact sunrise model and Lahiri formulation are validation hypotheses.
- Personal tithi birthdays/anniversaries and generic monthly recurrence remain
  intended scope. Runtime currently previews generic tithis, but named months and
  annual lunar dates explicitly fail closed pending exact month validation.
- The user profile is **religiously neutral**. Future supported festivals should
  show both labelled Smarta and Vaishnava dates in one consolidated reminder when
  different. No user sampradaya is assigned; this supersedes the first-Smarta-user
  suggestion below. Shared dates should not produce duplicate reminders.
- Do not implement festival rules now. Proposed named Vaishnava reference is
  ISKCON/Gaudiya, GBC Calendar Committee GCal 11, alongside Drik New Delhi Smartha;
  reference version/settings/independent output still require verification.
- Cautious exception policies and existing n8n/PostgreSQL authorization, identity
  and delivery safeguards remain. No migration, persistent scheduling, slot/job
  integration, private access, live send or deployment is authorized.

Current all-name/identity checkpoint (base0a1cae6): all12 ordinary names have
selected PAC and qualified Purnimanta research coverage. Logical identityv2 is
separate from profile provenance and date-selection policy. Proposed calendar-date
gate requires civil-date disagreements to be investigated/withheld; the actual300s
preview guard now matches documentation. Old60-second timing diagnostics remain
unchanged and failed where recorded. No scheduling adoption or migration.
See [coverage/identity/gate](M2F_MONTH_COVERAGE.md) for exact direct/inferred counts,
per-month cases, performance, tests and owner-gated future persistence mapping.

## Scope and requirements

| Requirement | Proposed behavior / exit condition |
| --- | --- |
| Personal birthdays/wedding anniversaries | Annual lunar-month + paksha + tithi recurrence, with named month convention and exceptional-date policy. Annual means the selected lunar month cycle, not a fixed Gregorian date or exactly one occurrence in every Jan–Dec year. |
| Monthly tithi | Select a fortnight/tithi, or both fortnights explicitly. Ekadashi = day 11; Purnima = Shukla 15; Amavasya = Krishna 15. A generic monthly tithi reminder must not be labelled an authenticated fasting observance. |
| Traditional observances | Separate versioned profiles for Ekadashi, Ram Navami, Janmashtami and Diwali/Lakshmi Puja, enabled individually only after tradition-specific verification. No universal festival rule is inferred from month/tithi alone. |
| Reminders and edits | Configurable time and advance notification, occurrence/series cancellation and overrides; every rule or policy change requires an authenticated owner proposal and explicit approval. Multiple notification slots need the storage decision below. |
| Telegram natural language | n8n/LLM may suggest structured intent; deterministic validation, human-readable rule/date preview and explicit owner confirmation precede persistence. Ambiguity produces a clarification, never a guess. |
| Future read-only queries | Today/tomorrow's sunrise Panchang plus tithi at a requested instant, transition times, month convention, location and calculation version; querying never creates a schedule. |

Owner-specified starting context: Delhi, Asia/Kolkata, Purnimanta preferred with
Amanta configurable. Exact coordinates/sunrise model and observance tradition
remain validation hypotheses/reference decisions. No owner sampradaya is assigned.
No other orchestrator begins before all Milestone 2 closes.

## Confirmed research facts and source assessment

Only first-party project documentation, publisher material and original calendar
research were used for the comparisons below. Published accuracy statements are
claims, not results verified at Phase 1. No package or dataset was executed in
that design checkpoint. The later authorized prototype acquisition and measured
results are recorded separately; no festival dates or final engine are certified.

### Calculation engines

| Candidate | Confirmed capabilities / licensing / maintenance evidence | Assessment and remaining work |
| --- | --- | --- |
| Skyfield + local JPL kernel | Python astronomy library, MIT license, NumPy binary dependency; almanac event search and sunrise routines. Official changelog lists 1.55 in August 2026. DE440s is documented as about 32 MB spanning 1849–2150. Local files allow offline operation. | **Recommended first candidate**, subject to tests. Explicit lunar month assignment, sidereal solar ingress/Lahiri convention and festival policies must be built/reviewed; Skyfield is not a Hindu observance engine. Cache/precompute bounded windows; measure CPU/RAM on the actual small VPS target rather than promise performance. |
| Swiss Ephemeris + Python binding | Native library with planetary, sidereal and rise/set interfaces. Licensor offers AGPL or professional licensing. Original pyswisseph README declares AGPL-3; licensor now names community pysweph and marks original pyswisseph unsupported. Current core documentation mentions DE441, while old wrapper README still describes DE431. | Strong alternative if owner accepts license obligations or obtains suitable rights covering core **and wrapper**. Do not assume buying a core license relicenses a particular wrapper. Pin exact core/binding/data/flags; inspect returned ephemeris mode and reject silent fallback. Native build/wheel support on chosen Python/architecture remains untested; community fork README reports breaking changes and a deprecated test suite, so its own tests cannot be assumed sufficient. |
| Astronomy Engine | MIT, Python implementation, solar/lunar positions, phase and rise/set searches; project describes testing against other astronomy tools and approximately arcminute accuracy. | Smaller-data alternative and useful independent numerical check. Its angular accuracy claim does not establish a tithi-boundary time tolerance. No packaged Purnimanta/festival policy; benchmark boundary error before selecting as authoritative engine. |
| drik-panchanga / PyJHora | Public Python Panchang implementations; repositories identify AGPL licensing, and drik-panchanga uses Swiss Ephemeris and lists festivals as TODO. | Study documented algorithms, not adopt as complete festival authority. They are not an independent astronomy engine when sharing Swiss data. No code copied; any reuse needs license review and a narrow dependency/security audit. |

Sources: [Skyfield license](https://raw.githubusercontent.com/skyfielders/python-skyfield/master/LICENSE),
[installation](https://rhodesmill.org/skyfield/installation.html),
[changelog](https://github.com/skyfielders/python-skyfield/blob/master/CHANGELOG.rst),
[kernel choices](https://rhodesmill.org/skyfield/planets.html),
[offline/local loading considerations](https://rhodesmill.org/skyfield/files.html),
[Swiss API/licensing](https://www.astro.com/swisseph/swephprg.htm),
[core data description](https://www.astro.com/swisseph/swephinfo_e.htm),
[original wrapper](https://raw.githubusercontent.com/astrorigin/pyswisseph/master/README.rst),
[licensor binding/support statement](https://www.astro.com/swisseph/secont_e_2609.pdf),
[community binding](https://github.com/sailorfe/pysweph),
[Astronomy Engine](https://github.com/cosinekitty/astronomy),
[drik-panchanga](https://github.com/webresh/drik-panchanga),
[PyJHora](https://github.com/naturalstupid/PyJHora).

Recommendation is a bounded Skyfield/DE440s feasibility stage, not an engine
adoption decision. Package, dependency and data-file rights/notices must be checked
for the exact pinned artifacts. Repository root license was not found in the
inspected license filename inventory; do not choose a project license implicitly.
A Skyfield implementation must not copy AGPL month/festival code while claiming
that MIT dependencies make the combined implementation permissively licensed.

### Independent Panchang references

| Reference | Confirmed value | Comparison limitations / acquisition policy |
| --- | --- | --- |
| IMD Positional Astronomy Centre, Rashtriya Panchang / Indian Astronomical Ephemeris | Institutional astronomical/calendar reference; publishes tithis and other elements, sunrise information and festivals with calculation explanations. | Its adopted central station is not Delhi; national civil solar months are not the proposed Hindu lunar selector. Match metadata before comparing sunrise/day/month labels. Use an identified edition/table, not a government holiday list as a timing oracle. |
| Drik Panchang | Location-aware daily calendars, Amanta/Purnimanta selection, separate Smartha/Vaishnava Ekadashi dates and Janmashtami guidance. | Independent publisher from PAC, but computational independence from our engine is unproven. Capture exact city/year/convention/tradition explicitly, not browser defaults. No bulk scraping or redistribution presumed authorized. |
| mypanchang.com | Publisher offers location and sampradaya-specific calendars and Amanta/Purnimanta choices. | Additional independent publisher for disputed observances; current opened homepage was Bangalore, not a Delhi fixture. Obtain exact Delhi/profile publication before treating any date as evidence. Algorithm/data lineage independence not established. |
| Original calendar literature | Sewell/Dikshit, The Indian Calendar, and Regulagedda Akshay's Panchanga-Tantra discuss calendar structure/observance distinctions. | Historical/research explanation, not a modern Delhi date oracle or universally accepted ritual tie-break specification. Do not transplant numerical models or regional rules without review. |

Sources: [IMD publication description](https://mausam.imd.gov.in/responsive/rashtriyPanchang.php),
[PAC calculation explanation](https://packolkata.imd.gov.in/panchang/en/explanation),
[Drik month settings](https://www.drikpanchang.com/settings/drikpanchang-settings.html),
[Delhi Ekadashi reference](https://www.drikpanchang.com/vrats/ekadashidates.html),
[Janmashtami reference](https://www.drikpanchang.com/dashavatara/lord-krishna/krishna-janmashtami-date-time.html),
[mypanchang publisher](https://www.mypanchang.com/),
[The Indian Calendar, institutional digitization](https://ignca.gov.in/Asi_data/34958.pdf),
[Panchanga-Tantra, original research](https://sanskritdocuments.org/articles/Indian_Calendar_System.pdf).
Only short independently reviewed numeric facts/metadata should enter fixtures,
with attribution and rights review; no copied publications/full calendar tables.
Disagreement is investigated by convention and metadata, not majority voting.

## Proposed calendar model

### Astronomy, sunrise date and ritual date are separate

Define elongation explicitly as `(Moon longitude - Sun longitude) modulo 360°`.
Tithi ordinal is `floor(elongation / 12°) + 1`: thirty half-open intervals.
Ordinal 1–15 is Shukla; 16–30 is Krishna,
with paksha-day 1–15. Store both forms consistently and reject impossible aliases.
A common longitude-origin shift cancels in the difference; sidereal solar ingress
and nakshatra still need an explicit ayanamsa. Use a documented apparent/true
longitude convention consistently, not mixed coordinate systems. These concepts
are described in [The Indian Calendar](https://ignca.gov.in/Asi_data/34958.pdf).

The engine adapter must solve **all transition instants**, not sample one value
per midnight/day and add 24 hours. Store UTC interval endpoints, solve around the
360° wrap, convert UTC/TT/UT1/TDB explicitly with pinned timescale data. Do not
round before deciding interval membership. [Skyfield timescale documentation](https://rhodesmill.org/skyfield/time.html)
explains the distinct time scales; its [almanac documentation](https://rhodesmill.org/skyfield/almanac.html)
also cautions about event-search cost.

For civil date D, compute its local sunrise S(D), then classify the interval
containing S(D). Separately answer tithi at an event's actual instant. A pre-dawn
birth may have a different sunrise-day label than its instant-based tithi;
request original local date/time/place when deriving a birthday and show the
choice. If the user already knows month/paksha/tithi, no birth timestamp is needed.
Do not infer a birth tithi from a Gregorian date at an assumed noon.

A festival policy consumes intervals plus sunrise/sunset/ritual windows and may
choose a different civil date. Reminder time is a fourth independent choice:
09:00 on the assigned date need not fall within that tithi. Preview this explicitly;
optional “while tithi active” timing needs its own approved rule.

### Location, sunrise and month convention

Recommended Delhi profile for owner review: WGS84 28.6139 N, 77.2090 E,
Asia/Kolkata; fixed level astronomical horizon, observer height 0 m for the
computational convention, not a claim of Delhi's physical elevation. Reference
fixtures must use their documented coordinates or record a comparison correction.
No automatic travel/location inference; changing location is a new proposal.

Propose a fixed apparent upper-limb sunrise convention with solar center at
-50 arcminutes, matching the documented Skyfield/USNO default. PAC documents
31 arcminutes refraction plus 16 arcminutes semidiameter (47 arcminutes).
These are **different models**; compare each to its matching reference, never
silently tune a default to force agreement. Pressure, refraction, horizon/dip and
geographic variation must be recorded. Sources: [Skyfield sunrise](https://rhodesmill.org/skyfield/almanac.html),
[PAC explanation](https://packolkata.imd.gov.in/panchang/en/explanation).

Use full lunation/new-moon/full-moon and sidereal solar-ingress records. Proposed
sidereal convention is an explicitly versioned Lahiri/Chitrapaksha specification;
Skyfield does not supply a drop-in approved Hindu month algorithm. The exact
ayanamsa expression/epoch and test reference remain a pre-adoption technical gate.

Purnimanta and Amanta are **different month boundary/label systems**, not display
translations. Store normalized month enum plus convention and intercalation
status, and preserve the original confirmed rule. Implement both from verified
boundary records; do not universally rename Krishna paksha by adding one to a
month number across Adhika/Kshaya transitions. [Drik's settings](https://www.drikpanchang.com/settings/drikpanchang-settings.html)
distinguish full-moon-ending and new-moon-ending months.

### Exceptional dates — proposed policy requiring owner approval

| Condition | Astronomy fact / explicit proposed scheduling behavior |
| --- | --- |
| Tithi spans two sunrises (vriddhi) | Return both candidate civil dates; personal/monthly default selects the **first** sunrise once, with policy visible in confirmation. Choosing second/both requires explicit rule; never duplicate by accident. Festival rules may differ. |
| Tithi spans no sunrise (kshaya tithi) | Interval still exists. Default **needs review**, no silent skip or substitute/send. Offer interval-start civil date or a named tradition fallback for owner selection; persist any approved fallback and its reason. |
| Adhika Maas | Detect lunation/solar-ingress structure; distinguish adhika and ordinary/nija month. Recommend ordinary-only for anniversaries unless explicitly selected otherwise; monthly all-lunation tithi schedules include adhika by explicit confirmation. Adhika-origin birthdays require a chosen policy; “both” may yield two celebrations and is not default. |
| Kshaya Maas | Rare missing month label differs from a skipped tithi. Detect and mark unresolved for review; do not substitute adjacent month, fabricate a month or borrow a festival policy. Automatic ritual handling is initially unsupported. |
| Exact transition at sunrise | Half-open [start,end) chooses the new tithi at equality. If numerical/reference uncertainty could cross sunrise, mark needs review rather than select using rounded display minutes. |
| Full/new moon and year/month changes | Purnima/Amavasya are tithi intervals, not just phase instants. Resolve month/paksha at the chosen instant and convention. No hardcoded Gregorian-year addition or fixed annual day count. |
| Different geography / no sunrise | Global geocentric transition instants and local sunrise assignment are distinct. Delhi first; non-Delhi profiles need acceptance. No-sunrise/polar or out-of-range data returns unsupported, not local midnight fallback. |

Recommendations in this table are product safety choices, **not universal ritual
rules**. A reviewed profile must encode the exact ingress/month naming algorithm
and exceptional-month pairing. Do not declare Kshaya-month automatic support on
an unverified Purnimanta conversion. Reference literature explains these calendar
phenomena; future fixtures must establish the selected modern convention.

## Observance policy layer

| Requested observance | Separate profile requirements before enabling |
| --- | --- |
| Ekadashi fasting | Explicit Smarta or a specifically named Vaishnava tradition; sunrise/arunodaya qualification, Dashami contamination, Mahadvadashi and tie-break exceptions. Generic day-11 reminders remain available as generic tithi recurrences. Parana windows are a later separately verified feature, never inferred from next sunrise alone. |
| Ram Navami | Chaitra Shukla Navami plus reviewed Madhyahna-window qualification and repeated/skipped-day precedence. Full Madhyahna definition/profile must be sourced and fixture-tested. |
| Janmashtami | Explicit tradition, Krishna Ashtami, convention-dependent month label and Nishita/Rohini qualification/precedence as applicable. A sunrise-only Ashtami filter is insufficient. |
| Diwali | Initially label **Diwali — Lakshmi Puja**; review Amavasya/Pradosha qualification and tradition-specific ties. Broader five-day Diwali calendar, regional alternatives and exact muhurta are distinct features, not implied. |

Evidence for the distinction: [Drik Ekadashi](https://www.drikpanchang.com/vrats/ekadashidates.html)
lists separate traditions; [Drik Janmashtami](https://www.drikpanchang.com/dashavatara/lord-krishna/krishna-janmashtami-date-time.html)
describes Nishita/Rohini selection. [Panchanga-Tantra pp.16–17](https://sanskritdocuments.org/articles/Indian_Calendar_System.pdf)
illustrates Madhyahna and Pradosha qualifications. That overview does **not**
settle the implementation's complete regional tie-break rules. Some guessed
Drik Ram Navami/Diwali page paths were inaccessible during research; no date or
complete rule is claimed from them. Obtain verified current publisher/profile
references before those observances are enabled.

Historical Phase 1 suggestion was a first Smarta profile. The owner now requires
a neutral user profile and paired labelled references; no sampradaya is assigned.
Unknown tradition, unsupported tie or conflicting references yields needs review.
Personal anniversary policy never inherits festival fasting rules automatically.

## Integration proposal — retain PostgreSQL, gateway and n8n

No component is replaced and no workflow is changed by this design. Recommended
future flow is within the existing application boundary:

```mermaid
flowchart LR
  T[Telegram owner] --> G[Existing authenticated gateway]
  G --> N[n8n intent and conversation]
  N --> V[Deterministic rule validation and preview]
  V --> P[Python Panchang calculation and policy]
  P --> C[Versioned candidate occurrences]
  C --> A[PostgreSQL proposal and explicit approval]
  A --> O[Approved occurrences and overrides]
  O --> R[Lease-checked reminder jobs]
  R --> G
```

No astronomy inside PL/Python, n8n Code or LLM output. A Python library/worker
within the existing application computes bounded immutable candidates offline;
n8n remains conversation/orchestration. Do not add a public service by default.
If a private callable endpoint is later needed, its authentication/network design
requires review. LLMs cannot approve changes or supply authoritative UTC dates.

Proposed logical records (DDL explicitly deferred):

- Calculation profile: engine/version/data hashes, timescale/ayanamsa/sunrise
  conventions, coordinates/timezone and supported range. Astronomy cache contains
  no names/chat IDs and is keyed by complete profile and interval, with bounded
  retention and no runtime download fallback.
- Hindu rule: annual-personal / monthly-tithi / observance kind; month/paksha/tithi,
  month convention/intercalation and skipped/repeated policies, observance profile
  where required, notification settings, validity bounds and rule revision.
- Candidate occurrence: immutable logical occurrence ID, physical lunar interval,
  assigned civil date, event instant/window, policy rationale, profile hashes and
  verification status. Unresolved candidates cannot enter the delivery queue.
- Proposal/approval snapshot binds rule, occurrence/override state, calculation
  version, date preview and reminder settings. Recheck under the existing common
  transaction advisory lock and row locks; reject stale or foreign decisions.

Current SQL generates Gregorian dates only. Existing hindu_rule fields do not
prove Hindu support; do not write Hindu JSON and expect existing generation to
use it. Recommend an additive Hindu proposal/approval/materialization path with
explicit dispatch and shared authorization/snapshot/conflict rules, preserving
Gregorian/legacy contracts. Exact migration/ACL design needs owner sign-off.

Extend the D10 managed-series boundary to Hindu series as part of that review:
0003 currently recognizes the m2d marker, so a new m2f marker alone would leave a
legacy-mutation gap. New and pre-conversion pending legacy requests must reject
Hindu-managed mutations too. Test current ownership at decision time under the
same lock. Conflict review must combine Gregorian and validated Hindu occurrences
over the explicit bounded horizon; missing candidate coverage blocks approval,
not silently means conflict-free.

Calculation/cache writers cannot approve rules or mutate delivery/audit history.
Use separately scoped staging/materialization privileges and trusted owner
identity, fixed SQL paths/parameterized values and immutable profile revisions.
Preserve worker/operator separation, SCRAM, local-only synthetic trust and
append-only reconciliation audit. Hashes detect changes but do not authenticate
an attacker-controlled replacement cache. Private birthday/person/chat data stays
out of public fixtures and logs; only non-personal astronomy can be shared.

### Identity, overrides and upgrades

Keep existing Gregorian `(event_id, occurrence_date)` and history untouched.
For Hindu recurrence propose a persistent logical key tied to event plus a
canonical numbered physical lunation and tithi/observance slot; do not key by
rounded UTC endpoints, translated month strings, Gregorian year or engine version.
Canonical lunation numbering must have a fixed epoch and tested engine-independent
mapping. A changed engine version cannot itself create a second occurrence.

Map that identity to an immutable original occurrence-date anchor for compatibility;
store assigned/display date separately. Moving a celebration or changing location
must preserve the occurrence and its cancellation/history, not create a new send
because the displayed civil date changed. Detect same-event/date collisions;
initially reject ambiguous two-occurrences-on-one-date cases rather than merge.
All migrations mapping old/new identities need isolated tests before approval.

Occurrence overrides/cancellations attach to stable identity; series changes show
a diff and retain prior overrides, including dormant ones, unless explicitly
approved otherwise. Engine/data/policy updates produce a reviewable versioned
recalculation: freeze approved/sent/uncertain history; replan only approved unsent
unleased future work. Require fresh approval for changed future assignments.
Automatic expansion of an already approved rule is allowed only under its pinned
profile/policy; any new ambiguity or unsupported edge is withheld for review.

### Advance reminders expose an existing storage limit

Current reminder materialization has one row per event/original date and due time
equal to occurrence start. It supports neither arbitrary advance offsets nor
multiple notification slots as a drop-in setting. The existing seven-day bounded
refresh window also cannot discover a 30-day advance reminder without looking
farther ahead. Do not claim those features already work.

Recommended staged decision:

1. First synthetic personal-rule slice uses one explicitly approved notification
   slot per occurrence, with independent due_at and event time; materialization
   horizon extends by the maximum approved lead time, bounded and tested. This
   requires a new reviewed path; passing 30 days into today's seven-day-limited
   refresh function is not a valid configuration change.
2. Full requirement adds stable notification slot IDs and deduplication by
   `(logical occurrence, channel, slot)`. Preferred design candidate is a companion
   job table for additional slots, preserving the existing ledger's uniqueness
   and historical rows. Share lease/receipt/quarantine semantics and the existing
   worker transport interface; do not run two delivery paths for the same slot.
   This is an **architecture/storage approval gate**, not implemented DDL.
3. Default candidate notification: day-of at 09:00 IST; optional one-day-before at
   18:00 IST, both explicitly shown before approval. Proposed cap: three slots,
   0–30 civil-day lead, user-configurable times. Same date/time slots deduplicate.
   Distinguish civil-day-at-time from exact-duration-before-event offsets.

Preserve five-attempt cap, definitive-rejection-only retry, lease-checked atomic
receipts, ambiguous-outcome quarantine and no blind resend/reset. A missed/past
advance notification is shown as missed, not automatically flooded on approval.
No production reconciliation privilege follows from Panchang support. Before
supporting more slots, isolate migration/rollback, token-race, stale ack, restart,
cancellation/replan and duplicate prevention tests for the changed functionality.

### Telegram confirmation and read-only query design

Example invented request: “Remind me of my anniversary on Kartik Krishna Ashtami
every year.” Clarify Purnimanta/Amanta, ordinary/adhika policy, date assignment,
location and notification time; do not assume “Diwali” or a birth timestamp.
Preview normalized Hindi/English aliases, annual vs monthly scope, lunar rule,
selected profile/exception policy, next three candidate dates, tithi intervals,
reminder times and unresolved years. Confirmation must bind a durable proposal ID
and fresh snapshot to the trusted private-chat owner. Natural-language “yes” only
approves the single identified current proposal, never an LLM-selected request.
Rejection leaves schedules unchanged; replay cannot apply twice.

A query “tomorrow's tithi?” uses the configured local civil date and returns tithi
at that day's sunrise plus transition times and month convention. “Tithi now?”
returns the instant-based value. Before sunrise or across midnight, explain the
difference instead of replacing one with the other. Queries require no schedule
approval and have no mutation/queue side effects; never send private birth data
to an external Panchang provider.

## Proposed fixtures and acceptance criteria (not executed)

Freeze reference URL/edition/page/date, retrieval date, numeric excerpt rights,
location/horizon/timezone, month convention/tradition, rounding precision and
source lineage for each golden fixture. Publisher independence is not proof of
independent ephemerides. Do not use the implementation to generate its own oracle.

| Test group | Proposed pass criteria |
| --- | --- |
| Transition solver | All 30 successive intervals monotonic/contiguous; exact half-open boundaries, new/full moon wrap, before/at/after boundary and timezone conversions. Root residual target <=1 second; this is numerical convergence, not guaranteed astronomical/reference accuracy. |
| Astronomy comparison | Matching-profile independent tithi transition references within proposed 60 seconds, explicitly accounting for published minute rounding. Compare sunrise within proposed 120 seconds only with matching coordinates/model. These are provisional engineering thresholds, not measured results; unexplained excess blocks release. |
| Boundary classification | No wrong civil-date/label is acceptable even when timing is within tolerance. Any boundary within a provisional two-minute uncertainty guard of sunrise/ritual cutoff is explicitly flagged for review; do not hide classification errors with wider tolerances. |
| Calendar naming | Full/new moon and month/year transitions, ordinary vs adhika both fortnights, Purnimanta/Amanta round-trips, rare Kshaya structure and no silent renaming. Independent real edge dates must be acquired and reviewed, not filled from guesses. |
| Personal recurrence | Invented known rules and invented timestamp-derived births before/after sunrise; 10 consecutive lunar years plus supported-range endpoints. One chosen date per eligible ordinary month cycle, documented review/skip/adhika policy, repeated-tithi dedup and missing-sunrise review. Gregorian year counts need not equal lunar-cycle counts. |
| Monthly recurrence | Both Ekadashis, Purnima/Amavasya, annual-cycle edges and intercalary months; all transitions discovered even if no sunrise samples the tithi. No generic tithi schedule labelled ritual fasting. |
| Observances | At least three complete consecutive years per enabled named profile, plus real independently identified skip/repeat/near-midnight/tradition-disagreement cases. Exact published observance date after metadata normalization; windows separately verified if offered. Each of four requested observances has its own enablement gate. |
| Geography | Delhi first; compare one other Indian location for sunrise-dependent date differences while geocentric transition instants agree. No-sunrise/out-of-range fail closed. No universal non-Delhi acceptance claim. |
| APIs and storage | No proposal mutation; trusted owner approval, stale/replay/foreign rejection, bounded conflicts, stable identity across date/profile changes, overrides/cancellations, immutable sent/uncertain history and complete no-op rebuild. Additional slots cannot bypass existing uniqueness. |
| Delivery and operation | Only synthetic transport mocks; negative/past lead times, bounded maximum lookahead, missing cache/data, process/DB restart, timeouts/expiry and no duplicate claims. No runtime network download or fallback engine; full required slot functionality tested before 2F closure. |
| Resource/maintainability | Offline deterministic cold/warm run on a small VPS-like budget, bounded one-location/year calculation, shared cache and measured RSS/CPU. Provisional budget <=256 MiB engine-worker RSS with <=512 MiB test limit; refine before approval if measurements disagree. Pin Python/dependencies/kernel/tzdata/timescale and record rebuild equivalence. |

Candidate research periods include an ordinary recent multi-year interval and a
2023 intercalary-month study; no unreviewed regional web result is adopted as a
Delhi fixture. Rare Kshaya-month real-data coverage is a known acquisition gap.
A synthetic anomaly alone cannot certify its real month naming/ritual handling.

## Phased implementation proposal and owner decisions

| Phase | Work after explicit approval | Gate / output |
| --- | --- | --- |
| F1 — completed design | Requirements, sources, engine/reference comparison, policies and architecture proposal | This document only; no engine, dependencies, migration or n8n change. |
| F2 — personal tithi first | Offline astronomy adapter feasibility, pinned profiles and independent fixtures; personal annual and generic monthly rules, ambiguity preview | Approve engine/license, Delhi/sunrise/ayanamsa choices and personal exception policy first. Then separate additive schema/API review; synthetic approval/identity/lead-time tests. |
| F3 — verified observances | Implement each named tradition's reviewed rule module with independent golden evidence | Owner chooses tradition and references. Keep unverified festivals disabled; all four requested profiles must pass before claiming complete 2F. |
| F4 — integration/acceptance | Approved companion slot/identity migration, n8n/gateway conversation wiring, configurable advance notifications, query API and full isolated acceptance | Preserve n8n and old APIs; 2B adoption still gates real workflow integration. Any real Telegram acceptance, production access or deployment needs separate approval. |

Original Phase 1 approval questions (scope now superseded only as recorded above):

1. Approve **Skyfield + pinned local DE440s** as the first feasibility candidate,
   with no AGPL dependency adoption; or choose Swiss with an explicit licensing
   and binding-support review. Exact Lahiri specification remains a validation gate.
2. Approve Delhi coordinates/profile, Purnimanta default with explicit Amanta, and
   the proposed 50-arcminute sunrise model (47-arcminute PAC comparison kept separate).
3. Approve personal defaults: first repeated sunrise once, skipped/no-month cases
   require review, ordinary-month-only anniversaries, adhika-origin policy asked
   explicitly; generic monthly tithi includes intercalary lunations when confirmed.
4. Select the initial ritual authority/tradition: proposed North-Indian Smarta
   candidate, or name the family's reference. Ekadashi, Janmashtami and Diwali
   variants must be specified; do not infer from geography.
5. Approve the stable logical Hindu occurrence identity and staged notification
   slot approach in principle before any migration. Full multi-slot companion job
   design, least-privilege SQL and compatibility require a concrete later review.
6. Approve the staged F2/F3/F4 plan, proposed notification limits and fixture/range
   targets. Proposed initial calculation range: 1900–2100 within the selected
   kernel, future preview/materialization bounded; historical birth accuracy and
   timezone limitations must be shown rather than silently extrapolated.

Initially unsupported: automatic Kshaya-month ritual substitutions; all sects or
regional calendars; travel auto-detection; polar/no-sunrise fallback; pre-1900
historical reconstruction; muhurta selection, astrology, shraddha, fasting advice
and unverified Parana times. Missing references/data yields unavailable/review,
not an LLM guess. Additional festivals remain disabled until independently tested.

## Checkpoint validation and boundaries

The original Phase 1 checkpoint used documentation-only checks. The separately
authorized isolated feasibility now has its own focused tests/report; no final
calendar accuracy or scheduling integration is accepted. No Docker, SQL execution,
package installation, private backup/manifest access, Telegram operation,
production change, deployment or merge. Phase 1 implemented no engine or migration; the later checkpoint adds only a
standalone astronomy prototype, with no persistent schema or integration.
2B remains blocked by unknown original manifest and missing exact-file read
approval; public Panchang research does not authorize private source adoption.
Stop after isolated feasibility for further review before persistent integration.
