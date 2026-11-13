# Current status: all-name coverage / identity v2 research

Pushed base0a1cae6 on development/m2f-skyfield-feasibility. See
[M2F_MONTH_COVERAGE.md](M2F_MONTH_COVERAGE.md) for current sources, per-month
matrix, proposed date gate and remaining approval requirements. Older measurements
below describe the prior checkpoint. No scheduling adoption. The preview loop's
120s/300s discrepancy was fixed; the new layer now actually applies300 seconds.

# Milestone 2F — general offline personal lunar previews

Research checkpoint from pushed `2bd37c09c4a3e25d4dcc3d6e7476c0665ac46b77`
on `development/m2f-skyfield-feasibility`, entry tree clean. HEAD/tracking agree;
GitHub confirmed the commit; no open PR. Owner authorizes arbitrary-rule offline
preview research, **not scheduling adoption**. No persistent occurrence, database,
n8n, Telegram or festival integration. Previous evidence fixtures remain unchanged.
See [current report](M2F_FEASIBILITY_RESULTS.md) and [handoff](HANDOFF.md).

## Reusable rule and identity

[recurrence.py](../prototypes/panchang/recurrence.py) accepts immutable LunarRule:
paksha (shukla/krishna), tithi (1–15), intercalation (ordinary/adhika/both),
convention (purnimanta/amanta), optional month, repeated policy (review/first/last)
and birth_basis metadata. Invalid input rejects; ordinary/Adhika is never inferred
from a religious profile. Default repeated behavior is review with no selected date.

## Logical identity v2, calculation provenance and selected date

Current research v2 separates the logical identity from calculation provenance:

```json
{"version":2,"convention":"purnimanta","month":"chaitra",
 "intercalation":"ordinary","lunation_cycle":324,"paksha":"shukla","tithi":9}
```

The fixed lunation-cycle discriminator is independent of ephemeris version and
selected Gregorian date. Profile hash/canonical new-moon date are separate
provenance; first/last/sunrise policy and selected civil date are separate selection
fields. Canonical ordinary Shravana Krishna/Shukla around Adhika share a cycle;
Adhika has another. The old v1 profile/date key is superseded for new research,
not automatically migrated. See [full contract, counts and proposed acceptance
gate](M2F_MONTH_COVERAGE.md) for fixed counting constants, conservative guard,
strict duplicate checks and owner-gated future mapping/persistence policy.
Engine/profile changes never authorize blind append/re-key. Offline comparison
withholds changed selected dates and rejects changed logical identity sets.

## General evaluation and birth interpretation

- `annual(rule, year)` evaluates the entire Gregorian civil search year, rather
  than an attested date window. Requires a named-month rule; does not convert a
  Vikrama/Shaka/regional era year. More than one matching occurrence is preserved;
  no exactly-one assumption or hardcoded reference date.
- `monthly(rule, start, end)` requires no fixed month and enumerates the requested
  fortnight/tithi over a bounded half-open civil window. `preview` also supports
  named rules in custom windows. All windows are at most 366 civil days; physical
  intervals must fit wholly inside 1900–2100 UTC. Internal pads never extend claims.
- `from_birth(instant, basis='instant' or 'sunrise')` explicitly distinguishes a
  timezone-aware event instant from Delhi sunrise on that civil day. For synthetic
  April 3, 2023 10:00 IST, instant yields Shukla13 while sunrise yields Shukla12.
  Ambiguous birth boundaries reject. Raw birth instants are not cached or logged.
  The returned rule retains birth_basis; **future recurrence date assignment stays
  sunrise-based** in both cases. No silent noon/birth-time substitution.
- The evaluator opens no fixture JSON, calls no service and saves no record. It
  calculates all matches from the pinned model, including years/rules absent from
  the old allowlist. Reference fixtures are read only by tests/evidence runner.
- All12 lunar names now have selected ordinary research coverage:47 direct PAC
  Amanta cases,47 explicitly inferred Purnimanta cases and5 new direct Purnimanta
  corroborations. This is not full independent certification of every year or
  exception. Unsupported context still returns no selected date/identity.
- Multiple ingresses/Kshaya, ambiguous solar/lunar boundaries or exceptional
  adjacent conversions yield unlabelled needs_review rows, not guessed dates.
  Unlabelled rows cannot safely be filtered out by a named rule, so they remain
  visible. Range violations reject the request. Empty results mean no match in
  this experimental calculation, not authoritative proof of no annual observance.

## Sunrise ambiguity policy

All candidate intervals are calculated before clipping to the preview window.
One sunrise: experimental selected date if the supporting month case is supported.
Two sunrises: default review with both dates; explicit first/last selects one.
Zero: skipped_at_sunrise, no date. Never select a neighboring day for a skipped
tithi. A first-policy event whose first sunrise is outside the window is not
reassigned to its second sunrise; last-policy can correctly include that second
day. Unresolved rows carry evidence/status and preserve the full sunrise list.

A **separate conservative 300-second calendar-date guard** withholds classification
where a sunrise/birth is too close to a solved tithi boundary. Lunar anchor
classification is similarly guarded. This is stricter date selection in the new
layer, **not a widened 60-second timing tolerance** and not a proven universal
physical-error bound. Existing astronomy's 0.1-second numerical and 120-second
review policies are unchanged. The pinned astronomy model, horizon hypotheses,
Lahiri candidate and accepted fixtures are unchanged.

## Calendar-date acceptance gate versus timing evidence

[calendar-references.json](../prototypes/panchang/calendar-references.json) records
finite independent public day-grid fixtures, scope and source metadata.
[recurrence-results.json](../prototypes/panchang/recurrence-results.json) records
all selected date/timing results, general annual/monthly output and performance.

Selected date gate requires published daily tithi agreement at Delhi sunrise
under **both** pinned sunrise hypotheses, greater than 300-second separation,
plus explicitly expected repeated/skipped policy outcomes. It passes 11 reference
rows (10 distinct dates), 22 hypothesis comparisons and six selection-policy cases.
This is a **selected fixture gate only**. Overall calendar adoption remains
incomplete: exact publisher model/coordinates differ or are unknown, not all
months/years/exceptions have independently direct golden coverage, and owner
engine/integration approval is absent. All API results retain
usable_for_scheduling=false and calendar_date_gate=not_adopted.

Independent evidence:

- Reuse pinned [Drik Delhi 2023 PDF](https://www.drikpanchang.com/download/hindu-calendar/2023/delhi/purnimanta/Hindu-Calendar-2023.pdf),
  v1.0.1, exact SHA/coordinates in fixtures. New selected page8 daily-grid facts:
  April2/3 Shukla12 repeated, April11 Krishna5, April12 Krishna7 (Krishna6 skipped).
  Pages14/16 verify daily tithis around ordinary/Adhika Shravana. Daily tithi
  readings are direct; month headers/context do not become direct month goldens.
  Existing parsed-PDF/no-visual-facsimile limitation remains.
- Primary [Drik March26,2026](https://www.drikpanchang.com/panchang/day-panchang.html?date=26%2F03%2F2026)
  explicitly reports Shukla Ashtami at sunrise, Navami after11:48IST;
  [March27](https://www.drikpanchang.com/panchang/day-panchang.html?date=27%2F03%2F2026)
  reports Navami at sunrise until10:06IST. The general personal Navami preview
  computes **March27**, matching daily classification. A March26 Smarta festival
  listing follows a different observance rule and is not a personal-date defect.
  No festival algorithm or owner sampradaya is inferred.
- [Panchangam.org March27](https://hindi.panchangam.org/dailypanchangam.php?date=2026-03-27)
  also identifies New Delhi Chaitra Shukla Navami, ending10:07IST. Distinct
  publisher, numerical engine independence unknown. It reports sunrise06:20
  versus Drik06:17; no assertion of matching horizon/coordinates. Parsed web
  facts/URLs are recorded without claiming a raw-page checksum.

The same March27 transition computes10:07:22.480IST: **+82.480s versus Drik**,
**+22.494s versus Panchangam.org** (different root brackets vary within0.05s).
Thus one new 60-second diagnostic fails, one passes, while both agree on the
calendar day. Old Drik/Himalayan differences remain unaltered and unexplained.
A publisher mismatch is recorded as disagreement until matching conventions,
independent evidence and a reproducible defect establish cause. No numerical
correction or tolerance increase. Future adoption needs broader direct calendar
goldens and an explicit owner-reviewed accuracy/date policy, not silent promotion
of the selected date-gate pass.

## Caching, performance and verification

Per evaluator: month diagnostics LRU32, preview LRU8, owned astronomy sunrise
cache bounded800. Cached month lookup uses exact interval containment with guards;
no interpolation, date-only classification or rounded new-moon replacement.
Preview cache returns deep copies; returned mutations cannot poison it. Keys
include immutable rule and window under the fixed profile. Profile drift clears
caches/rejects; different sunrise hypotheses have different profile IDs. Evaluator
owns the injected astronomy cache and is single-threaded; callers must not share
it between concurrent evaluations. No persistent or global user-result cache.

Measured on this development host: full 2026 Chaitra annual request **2.056s cold**,
identical warm request **0.000074s**, zero new month calculations and identical
output. Complete evidence run8.559s, peak RSS91,504KiB; bounded caches reached32/8.
This differs from the previous15-example workload and is not a like-for-like
speedup claim or VPS capacity certification. Existing one-thread BLAS, local
DE440s,512MiB/60CPU-second process limits and network audit guards reused.

12 new focused tests passed in18.563s. Materially affected date-evidence and cold
identity tests were rerun after extending fixtures; profile mutation guard was
verified separately. Tests cover arbitrary non-allowlisted year/rules, birth basis,
repeat/skip/window identity, canonical ordinary/Adhika anchors, unsupported names,
Kshaya/range/uncertain sunrise rejection, immutable/bounded caches, profile changes,
network-free operation, unchanged original evidence and disabled scheduling API.
Old implementation/tests/evidence remain untouched; unrelated accepted integration
and old timing experiments were not rerun. Reproduce with the README commands.

Stop after offline checkpoint. Preserve n8n/PostgreSQL architecture and approvals,
neutral user profile and future consolidated labelled Smarta/Vaishnava reminders.
No production/private backups/2B search, migrations, Telegram, deployment or merge.
