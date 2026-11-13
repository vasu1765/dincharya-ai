# Milestone 2F — lunar-month research validation checkpoint

Entry/current branch `development/m2f-skyfield-feasibility`, pushed base
`452bbcd28653ae8a8530ada57c3e0bd33e2f2d6b`; entry tree clean, HEAD and tracking
ref agreed and GitHub confirmed the pushed commit. This supersedes older
uncommitted-checkpoint/branch instructions below. The owner approved continued
research only, **not scheduling-engine adoption**. Git metadata is mounted read-only;
new changes are local until the explicit commands in [HANDOFF](HANDOFF.md) run.

## Current acceptance matrix

| Area | Result | Limit |
| --- | --- | --- |
| Multi-year Amanta | **21/21 selected date/ordinal/name/flag cases match** | 2023, 2024, early 2025; seven month names, not all 12 or whole years. Independent IMD PAC facts. |
| Purnimanta conversion | **18/18 selected comparisons match** | Seven explicit publisher-label corroborations; eleven calendar-context inferences, not 18 independently direct golden labels. Three remaining dates unvalidated for Purnimanta. |
| Adhika Shravana 2023 | Selected Shukla/Krishna and adjacent ordinary halves match | Does not certify other intercalary years or Kshaya neighbors. |
| New numeric tithi boundaries | **9/9 within unchanged 60 s gate** | Maximum absolute residual 24.829 s; whole-minute PAC references, not sub-second physical accuracy. |
| Lunar-year transition | **3/3 research-anchor checks match** | Ordinary Chaitra Shukla anchor year only; no Vikrama/Shaka/regional-era conversion. |
| Experimental annual examples | **15/15 evidence-bounded comparisons pass** | Includes two withheld skipped-tithi results; bounded examples, not exhaustive annual occurrence enumeration. Delhi sunrise remains a hypothesis. |
| Regression tests | **9 distinct new tests verified** | Initial eight passed; after adding final evidence examples, three affected/new tests passed. Existing accepted tests preserved. |
| Kshaya | **Rejects** | 1983-01-25 multiple-ingress period refuses both month conventions; no Kshaya naming/anniversary behavior inferred. |
| Original Drik/Himalayan timing gate | **Still failed/unexplained** | Original +85.886/+75.668 s and second-publisher discrepancy unchanged. No new distinguishing hypothesis evidence, so nine old experiments were not repeated. |
| General annual scheduling / adoption | **Disabled** | Public Astronomy.month_label/annual_preview still Unsupported. No scheduling integration. |

[month-results.json](../prototypes/panchang/month-results.json) records calculations;
[month-references.json](../prototypes/panchang/month-references.json) records public
facts, exact source pages, hashes, limitations and the explicit preview allowlist.
Previous references.json, research-references.json, feasibility-results.json and
validation-results.json are byte-for-byte preserved and hash-checked by the new
runner/tests. No old tolerance or assertion was removed.

## Public evidence, independence and provenance

Reused the accepted, pinned Skyfield/DE440s/ERFA environment; no new package or
kernel acquired. No private files or personal dates. Two finite public publication
downloads, with selected pages examined; no bulk site scraper or date-range crawl:

- [IMD PAC Rashtriya Panchang 1946 SE, 2024–25](https://packolkata.imd.gov.in/download/EnglishRP2425.zip),
  downloaded from the publisher's indexed English archive. ZIP 18,221,644 bytes,
  SHA-256 `e8aff02c95c47556e05ecab776fd2641ee6e5c4d2ec5f5d16652843c62546fb0`.
  Only known member RP_1946SE.pdf read through BytesIO (no extraction):
  19,037,639 bytes, SHA-256
  `226f8657efb4feaeb5840268bc8958af2229a8ee42ef175c55c6102e16255197`.
  Pages 23–28, 34, 100 and 106 provide selected daily lunar labels/time facts.
  This extends the already pinned 2023–24 PAC archive, not a replacement.
- [Drik Delhi 2023 Purnimanta calendar](https://www.drikpanchang.com/download/hindu-calendar/2023/delhi/purnimanta/Hindu-Calendar-2023.pdf),
  v1.0.1 created October 1, 2022; 1,239,904 bytes, SHA-256
  `2ec0b3eda6a7b6ac7c1a662fabb3e498b393fce4ebeafeb5968cb6632da834b0`.
  Page 1 specifies Delhi 28°39′07″ N, 77°13′53″ E, elevation 227 m,
  Asia/Kolkata. Pages 6/8/14/16 month headers/day grids and named full moons
  corroborate calendar context. These coordinates differ from prototype Delhi
  28.6139 N/77.2090 E and zero computational height; no matching-sunrise claim.
- [Drik Chaitra 2024](https://www.drikpanchang.com/festivals/lunar-month/festivals-chaitra.html?lang=en&year=2024)
  explicitly places northern Chaitra Krishna from March 26 and Chaitra Shukla
  new year April 9; April 17 has Chaitra Shukla Navami. Its festival listings
  corroborate labels only; **no festival rule is implemented or inferred**.
- [Drik April 1, 2024](https://www.drikpanchang.com/panchang/month-panchang.html?date=01/04/2024)
  explicitly distinguishes Phalguna Amanta / Chaitra Purnimanta, Krishna Saptami.
  [Drik new-year reference](https://www.drikpanchang.com/festivals/samvat-newyear/new-hindu-samvata-year-begins.html?time-format=24hour&year=2024)
  confirms the Chaitra Shukla transition. Dynamic pages can change location;
  metadata records the location actually returned. No raw-page hash claimed.
- The selected July 10 and August 10, 2023 primary Drik pages returned Bhadra
  (Rajasthan) and Washington DC respectively. They corroborate **only geocentric
  month names**, not Delhi sunrise, exact timing or location-equivalent daily
  tithi assignment. Both Adhika pakshas keep Shravana. Exact URLs/reading scope
  are recorded; July 25 has an explicit indexed primary Adhika label too.

Independent means separate from this implementation and, for Drik versus IMD,
a separate publisher. Shared engine/ephemeris lineage is unknown. PDF readings
used existing research-only pypdf 6.1.1 and manual selected date/tithi-line checks;
**no visual facsimile certification** is claimed. Dynamic primary/index readings
and calendar-context deductions are explicitly distinguished in the fixtures.
Raw ZIP/PDF/HTML captures remain outside Git. Minute rounding direction and
publisher internal numerical model are not invented. The attempted Delhi 2024
PDF URL returned 404; no third-party replacement was silently substituted.

## Model and month identities

[month_research.py](../prototypes/panchang/month_research.py) wraps the existing
explicit Lahiri candidate; it does not change that candidate or default astronomy.
Version: `lahiri1956-true-plus0.658as-iau1976-nut1980-fixed-origin-v1/paksha-conversion-v1`.
All candidate labels carry an unvalidated-research status and
usable_for_scheduling=false. Point queries remain hypotheses outside the corpus.

- Amanta: name and zero/one-ingress flag from the existing diagnostic. Multiple
  ingresses and ingress within 120 seconds of a new moon reject. No Kshaya name.
- Ordinary Purnimanta Shukla: same name as Amanta. Ordinary Purnimanta Krishna:
  following Amanta name, retaining the current **ordinary** flag even when the
  following lunation is Adhika. Adhika: retain current Amanta name/flag in both
  pakshas. This exception is validated for the selected 2023 Shravana cases,
  not every possible intercalation pattern.
- Consequently ordinary Shravana Krishna (July 4–17) and ordinary Shravana
  Shukla (August 17–31) surround the July 18–August 16 Adhika period. Do not
  assign Adhika to the preceding Krishna half or assume a Purnimanta named month
  must always be one contiguous full-moon interval. Returned amanta_start/end
  describe the physical backing lunation, not fictional Purnimanta month bounds.
- Research year token is the Gregorian year containing the most recent ordinary
  Chaitra Shukla new moon. It is not an era-year formula. March/April 2024
  Purnimanta Chaitra begins in Krishna before the April 9 new-year transition;
  the name can stay Chaitra while the research year anchor changes. Year search
  is bounded to 15 lunations and fails closed on an unsupported intervening case.
- Preview identity includes model version, convention, explicit Gregorian search
  year, month, ordinary/Adhika flag and ordinal. Repeated sunrises share one
  research identity; ordinary/Adhika identities differ. These are ephemeral
  research keys, **not approved PostgreSQL occurrence IDs**.

## Exact selected month cases

All instants below are 00:30 UTC (06:00 IST); these are **event-time classifications**,
not claims of identical tithi at a publisher's sunrise. Independent numeric boundary
fixtures and separate Delhi first-sunrise previews provide the date-selection checks.

| Date | Amanta | Purnimanta | Flag | Ordinal |
| --- | --- | --- | --- | --- |
| 2023-03-22 | chaitra | chaitra | ordinary | 1 |
| 2023-03-30 | chaitra | chaitra | ordinary | 9 |
| 2023-04-02 | chaitra | chaitra | ordinary | 12 |
| 2023-07-03 | ashadha | ashadha | ordinary | 15 |
| 2023-07-04 | ashadha | shravana | ordinary | 16 |
| 2023-07-10 | ashadha | shravana | ordinary | 23 |
| 2023-07-25 | shravana | shravana | adhika | 7 |
| 2023-08-01 | shravana | shravana | adhika | 15 |
| 2023-08-02 | shravana | shravana | adhika | 16 |
| 2023-08-10 | shravana | shravana | adhika | 25 |
| 2023-08-17 | shravana | shravana | ordinary | 1 |
| 2023-08-25 | shravana | shravana | ordinary | 9 |
| 2024-03-25 | phalguna | phalguna | ordinary | 15 |
| 2024-03-26 | phalguna | chaitra | ordinary | 16 |
| 2024-04-01 | phalguna | chaitra | ordinary | 22 |
| 2024-04-08 | phalguna | chaitra | ordinary | 30 |
| 2024-04-09 | chaitra | chaitra | ordinary | 1 |
| 2024-04-17 | chaitra | chaitra | ordinary | 9 |
| 2024-05-10 | vaishakha | unvalidated | ordinary | 3 |
| 2025-01-20 | pausha | unvalidated | ordinary | 21 |
| 2025-02-09 | magha | unvalidated | ordinary | 12 |

Purnimanta evidence kinds: seven direct publisher-label corroborations and eleven
context deductions are recorded per row. A numerical match to a deduction does
not promote it to an independently direct reference. 2024 Vaishakha and 2025
Pausha/Magha Purnimanta were not asserted merely because the candidate computes them.

Nine new boundary deltas (calculated minus PAC, seconds):
-7.910, +17.606, -11.453, +19.638, +21.890, -20.462, -8.432, -24.829, +15.298.
The original 60-second gate is unchanged; these passes do not resolve the old
Drik/Himalayan failures. No generic correction or tolerance change was attempted.

## Experimental anniversary previews: tightly bounded evidence examples

`annual_example(year, month, ordinal, intercalation, convention)` accepts only
15 exact allowlisted combinations. year is an explicit **Gregorian search year**;
ordinary/Adhika must be supplied. It calculates the occurrence, checks month/flag,
compares sunrise list and selected date to the evidence fixture, and rejects
ambiguous/mismatched results. It never returns a stored date instead of computing.
These are bounded examples around an attested occurrence, not proof of finding
all matches in a full year. An unknown rule/year rejects rather than returning
an empty list or extrapolated birthday. No personal data or persistent approval
API is involved. No holiday/ritual authority is assigned to the owner.

| Search year / rule | Experimental date result | Conventions |
| --- | --- | --- |
| 2023 Chaitra Shukla 9 | March 30 | Both |
| 2024 Chaitra Shukla 9 | April 17 | Both |
| 2023 Chaitra Shukla 12 | April 2, first of April 2/3 repeated sunrises; one preview | Both |
| 2024 Krishna 14 | No sunrise match; needs_review, no selected date | Amanta Phalguna / Purnimanta Chaitra |
| 2023 Shravana Shukla 9, Adhika | July 27 | Both |
| 2023 Shravana Shukla 9, ordinary | August 25 | Both |
| 2025 Magha Shukla 12 | February 9 | Amanta only |
| 2024 Krishna 7 | April 1 | Amanta Phalguna / Purnimanta Chaitra |

The 120-second boundary-review policy remains. Exact/near numerical full/new moons
reject. Repeated dates select first once; skipped dates return no guessed fallback.
No date substitution, previous-day observance, automatic Adhika anniversary choice
or Kshaya handling is introduced. Publisher minute rounding and experimental
sunrise-model limitations remain material; this is not scheduling adoption.

## Verification, performance and remaining blockers

Nine distinct new regression tests cover independent multi-year labels and pakshas,
ordinary/Adhika identity, year transition, all allowlisted examples, repeated/skipped
selection, stable/different research keys, discrepant calculation or unsupported rule/year
rejection, exact/near boundaries, out-of-range inputs, real multiple-ingress
rejection and network-free computation. Initial eight tests passed in 36.669 s;
final three affected/new tests passed in 41.061 s after extending evidence.
No unrelated suites or previously accepted coordinate experiments were rerun.
The offline runner checked every selected case and previous evidence hashes;
exit **2**, never an adoption success signal.

Final recorded metrics: 40.546 s wall, 40.543 s CPU, peak RSS 56,008 KiB.
Same pinned dependencies, explicit local DE440s, one-thread BLAS, Python network
connection/DNS/bind audit guards, 512 MiB address-space / 60 CPU-second limits.
The bounded Chaitra back-search is deliberately simple and relatively expensive;
no small-VPS runtime or long-range physical timing certification is claimed.
Failure/resource-limit exhaustion yields no preview fallback.

Remaining: five untested month names, broader years/Adhika patterns, direct
Purnimanta golden coverage replacing context deductions, precise independent
Lahiri epoch verification, matching Delhi sunrise metadata and original timing
failures. Kshaya neighbors/era conversion/general annual enumeration remain
unvalidated. Continued research may extend public numeric fixtures; engine
adoption, birth-record interpretation/policy and persistent integration need
further review. Neutral profile and future consolidated labelled Smarta/Vaishnava
observances stay unchanged; no festival rules, n8n/database/Telegram operations,
production/private backup/2B access, deployment or merge. Stop for ChatGPT review.

---

## Prior pushed validation evidence (452bbcd; historical below)

# Milestone 2F — focused validation checkpoint

Latest pushed base: `6f1f0b72729023d84123891725fd0b018bc1c584` on
`development/m2f-skyfield-feasibility`; entry tree clean, local/tracking and GitHub
commit agreed. No open PR found. The owner accepted that prototype as research,
**not scheduling engine adoption**. This follow-up is uncommitted until the owner
runs the explicit safe-file commands in [HANDOFF](HANDOFF.md); Git is read-only.
The original feasibility report below is historical evidence, not current Git state.

## Current pass/fail matrix

| Gate | Result | Scope / limitation |
| --- | --- | --- |
| Reproduce original comparisons | PASS reproduction | Unchanged reference bytes; original Drik +85.886/+75.668 seconds reproduced. |
| Original 60-second tithi accuracy gate | **FAIL** | Drik differences remain unexplained; no tolerance increase, timestamp correction or fixture substitution. |
| Controlled coordinate hypotheses | No explanation | Nine position/frame combinations; none brings both Drik rows within 60 seconds. |
| Additional independent publication evidence | Mixed | USNO 1/1 and IMD PAC 3/3 within 60 seconds; Himalayan Academy 1/2, with another 154-second discrepancy. Publisher independence is not guaranteed engine independence. |
| Boundary/range regressions | PASS | Wrap, tiny search intervals, exact/near boundaries, lower/upper range, sunrise and monthly previews tested; unsupported full intervals fail closed. |
| Exact versioned Lahiri candidate | Selected checks PASS; adoption incomplete | Three vendor-reproduced epoch values within 0.002 arcsecond; independent PAC sub-arcsecond epoch validation remains missing. |
| Sidereal solar ingress | Selected 2023 cases PASS | Four PAC increasing-ayanamsa ingress times within 27 seconds, using unchanged 60-second comparison threshold. Not a 1900–2100 certification. |
| Amanta naming | Selected research cases PASS; public API disabled | Chaitra ordinary, Shravana Adhika, Shravana ordinary match PAC. No general named-calendar claim. |
| Purnimanta naming / Kshaya / annual dates | **UNSUPPORTED** | Physical full-moon boundaries are distinct from verified name conversion; public named-month/annual APIs still reject. |
| Scheduling adoption | **BLOCKED** | Accuracy, sunrise metadata, general month/exception validation and further owner review remain gates. |

23 focused tests passed in **4.531 seconds**. Only affected astronomy tests ran;
no 2C/2D/2E, reconciliation, Docker/n8n/live Telegram acceptance was repeated.
The validation CLI exited **2**, intentionally retaining `usable_for_scheduling=false`.
Full numeric comparisons and source metadata are in
[validation-results.json](../prototypes/panchang/validation-results.json) and
[research-references.json](../prototypes/panchang/research-references.json).
The original references.json and feasibility-results.json remain byte-for-byte
unchanged, preserving accepted research evidence.

## Controlled tithi investigation

All rows use the same DE440s, timescale data, bisection and five original fixtures.
Apparent includes light-time, aberration and deflection; astrometric retains
light-time without apparent corrections; geometric uses simultaneous geocentric
vectors. Frames are Skyfield true ecliptic/equinox of date, mean ecliptic/equinox
of date, and fixed J2000 ecliptic. Mean-date rotation uses Skyfield's pinned
mean-obliquity/precession implementation. These are labelled diagnostic choices,
not changes to default geocentric apparent true-date behavior.

Deltas below are calculated minus published seconds, ordered NASA Jul 17 new
moon, Aug 1 full moon, Aug 16 new moon, Drik Jan 13 and Jan 14 2026:

| Position | Frame | NASA three deltas (s) | Drik two deltas (s) |
| --- | --- | --- | --- |
| apparent | true_date | -9.805 / +40.320 / +11.261 | +85.886 / +75.668 |
| apparent | mean_date | -9.805 / +40.320 / +11.261 | +85.886 / +75.668 |
| apparent | J2000 | -8.762 / +41.418 / +12.909 | +84.622 / +74.872 |
| astrometric | true_date | -9.970 / +107.968 / +11.124 | +108.765 / +90.665 |
| astrometric | mean_date | -9.970 / +107.968 / +11.124 | +108.765 / +90.665 |
| astrometric | J2000 | -8.926 / +109.067 / +12.772 | +107.529 / +89.868 |
| geometric | true_date | +32.465 / +72.812 / +54.410 | +130.600 / +120.218 |
| geometric | mean_date | +32.465 / +72.812 / +54.382 | +130.600 / +120.218 |
| geometric | J2000 | +33.508 / +73.911 / +56.058 | +129.364 / +119.421 |

True versus mean date cancels almost entirely in the Moon-minus-Sun longitude;
fixed J2000 shifts these examples by only about 1–2 seconds. Removing apparent
corrections does not resolve Drik and worsens some phase comparisons. Geometric
positions do not resolve it either. No claim that location, publisher rounding,
time scale or ayanamsa explains the residual: the two tithi longitudes share the
same sidereal offset, so substituting a Lahiri offset cannot repair elongation.
Unknown publisher numerical lineage/model remains a limitation, not an explanation.
The numerical solver's <=0.05-second bracket is not physical timing accuracy.

## Additional public reference evidence

- [USNO 2026 phases](https://aa.usno.navy.mil/calculated/moon/phases?year=2026):
  Jan 18 new moon 19:52 Universal Time. Delta **-1.071 seconds**. Modern UT/UTC
  difference is sub-second; whole-minute publication does not establish
  sub-second accuracy. This successful lookup supersedes the prior DNS failure.
- [IMD PAC Rashtriya Panchang 1945 SE / 2023–24 archive](https://packolkata.imd.gov.in/download/EnglishRP2324.zip):
  PDF pages 51/59 give Jul 17 Amavasya ending 24:02 IST, Jul 18 Pratipad ending
  26:10 IST and Aug 16 Amavasya ending 15:08 IST. Normalize >24h onto the next
  civil day. Deltas **-9.805 / +23.209 / +11.261 seconds**. These are global
  geocentric transition times, not matching-model Delhi sunrise validation.
- [Himalayan Academy/Gurudeva New Delhi 2025–26 calendar](https://minimela.com/wp-content/uploads/panchangam/2025-2026/world/new_delhi_india.pdf),
  PDF page 38: Jan 13 Dashami until 15:21 IST; Jan 14 Ekadashi until 17:53 IST.
  Deltas **-154.138 / +15.656 seconds**. Footer reports calculation Dec 20, 2023,
  local standard time. Exact coordinates, horizon and engine lineage unknown.
  Web-parsed text only; screenshot unavailable, so reading remains provisional.
  This disagreement is retained, not used to replace the Drik fixtures.

IMD archive: 16,495,663 bytes, SHA-256
`38c50c8d11071369e895ec21e09120be49ab576f6a40334965da7eb22b7b8522`.
Known ZIP member `RP_1945SE.pdf`: 17,605,534 bytes, SHA-256
`9ba9dd3970a45787edafd619787b91d83557fa4b7c9344738316e8b8d73757c4`.
Only numeric excerpts are recorded in Git. The public PDF stayed outside Git;
known-member BytesIO parsing with pypdf 6.1.1 avoided archive extraction. This
research parser is not a runtime dependency. Page numbers above are one-based
PDF pages; ingress page 178 is printed page 158. Text extraction has not been
visually certified. Publication precision is whole minutes / whole arcseconds;
rounding direction and exact computation models are not assumed.

## Range and numerical fixes

Demonstrated failures before the fixes included an IEEE tiny-negative modulo
rounding to 360 (possible ordinal 31), constant/indistinguishable sample motion,
contradictory classification within a solved transition's numerical bracket,
exposed month/tithi bounds outside 1900–2100, valid lower previews failing because
of unrelated padding and upper previews rejecting the exclusive end sentinel.
A bad sunrise model type raised TypeError instead of a sanitized Unsupported.

- Six-hour brackets must show finite strictly positive motion below 12 degrees,
  with no multi-bin jump. All 30 ordinals and 30→1 wrap are tested. This validates
  the physical-model sampling hypothesis for exercised cases, not arbitrary
  adversarial motion completing a hidden full revolution between samples.
- Algebraic exact angles follow half-open bins. Reported transition instants and
  +/-millisecond neighborhoods fail closed within **0.1 seconds** for interval,
  month-boundary and search-endpoint membership. Search endpoints use tiny
  internal pads to avoid silently dropping/doubling an uncertain crossing.
  +/-1-second interval results require review under the existing **120-second**
  astronomical review guard. Raw tithi_at remains an experimental point estimate,
  not a boundary-safe scheduling decision. No physical accuracy gate is loosened.
- Raw instants are supported on `[1900-01-01 UTC, 2101-01-01 UTC)`; transition
  windows allow the upper instant only as end sentinel. Complete tithi/month
  intervals must lie wholly inside that range. Padding may solve roots internally
  but cannot extend calendar claims. Thus raw sunrise Jan 1, 1900 computes while
  its straddling tithi interval fails closed; raw upper-end tithi computes while
  its straddling interval also fails closed. The original endpoint test was
  corrected to assert this stricter distinction, not removed.
- Monthly Jan 2, 1900 and Dec 31, 2100 previews pass; partial lower-bound tithi
  and unsupported civil windows reject. Out-of-range sunrise/month searches and
  sub-timescale-resolution transition searches reject. Unaffected recurrence,
  first-of-repeated and skipped-at-sunrise policies remain as before.

## Reproducible Lahiri hypothesis and limited month evidence

Research-only profile:
`lahiri1956-true-plus0.658as-iau1976-nut1980-fixed-origin-v1`.
Anchor a fixed J2000-mean-equator direction to true tropical ecliptic longitude
23°15′00.658″ at **JD TT 2435553.5** (1956-03-21 00 TT). Transport it with
ERFA IAU1976 precession, IAU1980 nutation and IAU1980 obliquity. Transform the
apparent solar ICRS vector into the same frame before subtracting the origin;
never combine mismatched tropical/true/mean coordinate conventions.
This is an explicit reproducible candidate, not every system called “Lahiri”.

[Swiss Ephemeris documentation Appendix E](https://www.astro.com/swisseph/swisseph.htm)
provides this reproduction convention and 2019 Jan 1/4/7 epoch values.
Candidate errors are -0.001120/-0.001113/-0.001086 arcseconds against that table;
a separately retained uncorrected 23°15′00″ anchor misses by about -0.659 arcsecond.
This table is a vendor reproduction of IAE, **not independent PAC epoch data**.
No Swiss library was installed and no AGPL code copied. New hash-locked
pyerfa **2.0.1.5**, embedded ERFA **2.0.1**, SOFA **20231011**, supplies the matrices
under its permissive distribution notices; exact wheel/hash is in the lock and
metadata. Existing Skyfield baseline calculations and original fixtures stay fixed.

PAC explanatory page 12 distinguishes fixed 23°15′ civil solar-month calculations
from **increasing ayanamsa used for lunar intercalation**. Do not validate lunar
names against the fixed civil table. Its page 178 increasing-ayanamsa ingress table
supports these comparisons:

| Ingress | Published IST | Candidate minus reference |
| --- | --- | --- |
| Mesha | Apr 14, 2023 14:59 | -2.225 s |
| Karkata | Jul 16 29:07 = Jul 17 05:07 | +6.303 s |
| Simha | Aug 17 13:33 | -26.161 s |
| Kanya | Sep 17 13:31 | -3.749 s |

The candidate has one ingress for ordinary Chaitra (March 21–April 20 lunation),
zero for Adhika Shravana (July 17–August 16), and one for ordinary Shravana
(August 16–September 15). PAC pages 22/51/59 independently name these periods.
These **three selected Amanta research cases** agree. A diagnostic returns
explicitly labelled candidate fields only. Public month_label and annual_preview
still reject; Purnimanta physical full-moon bounds are not name conversion.
Two ingresses (Kshaya) and solar ingress within 120 seconds on either side of a
lunar boundary reject, including an ingress just outside the lunation. Kshaya,
exceptional conversions and general years remain unsupported.
PAC's March 22 ayanamsa 24°10′43″ has no specified instant within the day, so no
sub-arcsecond epoch pass is claimed from that rounded datum. Before adoption,
obtain independently specified epoch instants/models and multi-year fixtures,
validate seasonal/month transitions, Purnimanta naming and exception policies.

## Reproduction and remaining gate

Use the exact offline commands in [prototype README](../prototypes/panchang/README.md).
The new validation runner checks the unchanged original-reference SHA, runs all
nine hypotheses and every recorded additional fixture, and records failures as
well as passes. Network/DNS/bind audit guards precede astronomy imports. Same
512 MiB address-space / 60 CPU-second limits, one-thread BLAS. Recorded follow-up
experiment after imports: **2.254 s wall, 2.256 s CPU, peak RSS 56,792 KiB** on this
development host; not VPS capacity or historical/future timing certification.
Resource limits contain the process but are not an OS network sandbox.

Stop for ChatGPT/owner review. No engine adoption, persistent schedules, annual
output, festivals, migrations, n8n modifications, Telegram calls, private inputs,
production access, deployments or merges. Remaining blockers: unexplained Drik
and provisional second-publisher differences, matched sunrise metadata, independent
precise epoch data, broader Amanta validation, Purnimanta/exception semantics and
separate integration approval. 2B original-manifest identification/access is still
blocked and is unrelated to this public-data research checkpoint.

---

## Historical accepted feasibility checkpoint (before follow-up validation)

# Milestone 2F — isolated Skyfield feasibility checkpoint

Base: pushed `952475720e1990f635eed7f1710b123018262db0`, branch
development/m2-recovery-acceptance; clean working tree at entry. HEAD and origin
tracking ref agreed and GitHub confirmed the commit. Git metadata remains mounted
read-only, so no new branch/commit was created here. Suggested separate branch:
development/m2f-skyfield-feasibility (owner commands in HANDOFF).

Outcome: **useful astronomy prototype; not ready for scheduling or final engine
adoption**. Eleven focused tests passed, but two independent tithi comparisons
exceed the unchanged provisional 60-second threshold. Exact Lahiri and month-name
semantics are not validated; annual birthday/anniversary dates fail closed.
No persistent integration follows from this feasibility authorization.

## Exact environment and provenance

- Linux x86_64, CPython 3.12.3; Skyfield 1.55, NumPy 2.3.4, jplephem 2.23,
  sgp4 2.25, certifi 2025.10.5. All wheels acquired from explicit public PyPI with
  a clean environment/config, installed in a separate /tmp venv using an offline
  hash-locked install. No production Python environment or index credentials.
- DE440s acquired from the [public JPL HTTPS endpoint](https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440s.bsp):
  32,726,016 bytes; SHA-256
  c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2.
  This hash is locally recorded integrity evidence, not an independently signed
  publisher assertion. Kernel and wheels remain outside Git.
- [ephemeris.json](../prototypes/panchang/ephemeris.json) records wheel and
  bundled timescale/nutation/TZif hashes. Exact reviewed wheel artifacts are in
  [requirements.txt](../prototypes/panchang/requirements.txt), for this platform
  only. Skyfield MIT and JPL source documentation were reviewed in the design;
  no Swiss/AGPL implementation was installed or copied.
- The local astronomy code pins builtin Skyfield timescale data, disables runtime
  downloads and uses apparent geocentric true-ecliptic/equinox-of-date longitudes.
  TT/TDB handling is delegated to Skyfield; UTC output uses pinned conversion
  data. Supported computation range is 1900–2100, not certified timing accuracy
  throughout that range. Long-range Delta-T/UT1 prediction remains a limitation.
- Delhi hypothesis: WGS84 28.6139 N, 77.2090 E, Asia/Kolkata, zero computational
  observer height/level horizon. Two explicitly labelled fixed center-altitude
  models: -50 arcminutes and a -47 arcminute PAC-comparison hypothesis. Neither
  is silently accepted as the owner's final sunrise model.

## Implemented and tested

The standalone [prototype](../prototypes/panchang/astronomy.py) has no DB, gateway,
n8n, Telegram or festival dependency. It finds every 12-degree Moon-minus-Sun
elongation crossing using six-hour vector samples and bisection, with a maximum
0.05-second numerical bracket. Adjacent interval membership is half-open; outputs
near a boundary require review. This convergence bound is **not** an independent
astronomical accuracy measurement.

| Capability / test | Verified result |
| --- | --- |
| Full lunar-cycle transitions | All 30 ordinals found in sequence, monotonic timestamps, correct 30→1 wrap; before/after every transition checked and identical inputs repeat exactly. |
| Event instant versus sunrise | On Jan 13, 2026 Delhi sunrise classified ordinal 25; 18:00 IST classified ordinal 26. Equivalent UTC/local instants agree. No assumed-noon birthday conversion. |
| Sunrise and near-boundary handling | Both fixed models yield one sunrise; 47-arcminute model is about 14.96 seconds later on the reference date. Synthetic sunrise within a transition's uncertainty guard is flagged for review. |
| Repeated tithi | Experimental ordinal 9 interval spans Delhi sunrises Nov 18 and 19, 2026; generic monthly preview chooses first once, not two reminders. These dates are prototype structural fixtures, not independently verified festival dates. |
| Skipped tithi | Experimental ordinal 11 runs between sunrises Nov 20–21, 2026; preview has no selected date and needs_review. No guessed substitute/automatic send. |
| Physical month boundaries | For Jul 25, 2023, Amanta boundary interval is Jul 17–Aug 16; Purnimanta is Jul 3–Aug 1, using new/full moon transitions. Month-name field remains NULL/unsupported. |
| Intercalary investigation | Jul 17–Aug 16, 2023 lunation has zero sidereal-sign crossings under constant 24.0/24.2/24.5-degree sensitivity hypotheses; next ordinary lunation has one. These constants are explicitly **not Lahiri**; this is not a general validated Adhika/month-name API. |
| Failure boundaries | Naive/unsupported dates, reversed/oversized ranges, bad tithi/convention/model, missing/symlinked/wrong-size/wrong-hash kernel and changed dependencies reject. 1900/2100 instant endpoints are computationally exercised. Annual/month-label calls explicitly reject. |
| Offline execution | Runtime uses explicit local files; network patch test passes. Experiment installs Python socket/DNS/bind audit guards before prototype import; no runtime network call required. Not an OS network sandbox. |

11 tests passed in the final scoped run (1.581 seconds). Only those new tests were
run; 2C/2D/2E/reconciliation/n8n/live acceptance was not repeated. An earlier scoped
run passed before adding the timezone hash; only this materially affected prototype
suite/experiment was repeated. No existing tests or tolerances were weakened.

## Independently sourced comparison results

The exact small public numeric fixtures, URLs, display precision and known/unknown
metadata are in [references.json](../prototypes/panchang/references.json).
[NASA GSFC phase tables](https://eclipse.gsfc.nasa.gov/phase/phase2001gmt.html)
provide Universal Time, whole-minute values. We treat modern UT as UTC within
one second for these comparisons, not as an exact subsecond UTC oracle.
[Drik's explicit New Delhi 2026 listing](https://www.drikpanchang.com/vrats/ekadashidates.html?year=2026&geoname-id=1261481)
provides tithi endpoints in IST. Neither page's exact rounding algorithm is
established. Geocentric tithi timing is distinct from observer-specific sunrise;
Drik longitude/ephemeris flags remain unconfirmed.

| Reference instant | Prototype UTC result | Signed difference | 60-second numeric gate |
| --- | --- | --- | --- |
| NASA new moon Jul 17, 2023 18:32 UT | 18:31:50.195 | -9.805 s | Within |
| NASA full moon Aug 1, 2023 18:31 UT | 18:31:40.320 | +40.320 s | Within |
| NASA new moon Aug 16, 2023 09:38 UT | 09:38:11.261 | +11.261 s | Within |
| Drik Krishna Ekadashi start Jan 13, 2026 15:17 IST | 09:48:25.886 | +85.886 s | **Outside** |
| Drik next tithi start Jan 14, 2026 17:52 IST | 12:23:15.668 | +75.668 s | **Outside** |

No threshold widening, averaging or selection of a more convenient ephemeris was
used. Rounding alone is not established as the cause of the two outside results.
Coordinate conventions, apparent/geometric longitude choices, reference lineage
and numerical model differences need a separate controlled comparison. These are
unresolved accuracy discrepancies, not proof that either calendar is wrong.
Even NASA's within-60-second results do not certify the exact apparent-coordinate
convention or all 30 intermediate tithis against an independent oracle.

For sunrise, [Drik's New Delhi page](https://www.drikpanchang.com/telugu/panchanga/telugu-day-panchanga.html?date=14/01/2026&lang=en)
publishes 07:15 IST on Jan 14, 2026; prototype gives 07:15:04.925. Numerically close,
but the retrieved page does not establish exact coordinates/elevation/horizon
flags, so **not a matching-profile sunrise validation pass**. A direct public USNO
request for our exact Delhi coordinates failed DNS resolution; no reference was
invented or silently replaced. Some other reference URLs were inaccessible.

Machine-readable measurements and all comparison pass/fail flags are retained in
[feasibility-results.json](../prototypes/panchang/feasibility-results.json). CLI
returns exit 2, feasibility_incomplete_not_for_scheduling, usable_for_scheduling=false.
Exit 1 denotes unavailable/invalid execution. Unit-test success must not be read
as external-reference accuracy acceptance.

## Lunar months and exact Lahiri — findings and unsupported areas

[Swiss Ephemeris's published discussion](https://www.astro.com/swisseph/swisseph.htm)
distinguishes Lahiri variants and describes the ICRC 1956-03-21 00:00 ephemeris-time
23°15′ anchor, a later 0.658-arcsecond correction, true versus mean equinox issues,
and IAU1976/1980 choices when reproducing particular IAE tables. That is evidence
that the name “Lahiri” alone is insufficient; we did not copy AGPL code or adopt
a constant offset as its implementation. No exact formula/epoch/precession/nutation
combination has yet been independently validated against a pinned PAC/IAE table.

Physical new/full moon boundaries can be calculated without ayanamsa. Named
months, ingress counting near boundaries and Purnimanta/Amanta **label conversion**
need the reviewed solar sidereal convention plus intercalary rules. A new-moon
interval is not automatically a correctly named Purnimanta month. The known July
2023 period is independently described as intercalary in
[mypanchang's July 2023 Pune reference](https://www.mypanchang.com/phppanchang.php?cityhead=Pune%2C+Maharastra&cityname=Pune-Maharastra-India&mn=6&monthtype=1&yr=2023);
its city is not reused as Delhi sunrise evidence.

The prototype therefore returns diagnostic bounds/offset sensitivity only and
raises Unsupported for month labels and annual birthdays/anniversaries. General
Adhika/Kshaya classification and exceptional Purnimanta conversion remain
unsupported. Personal annual/monthly requirements remain scope, but annual date
output cannot safely be enabled at this checkpoint. This is a documented
feasibility limitation, not a substituted or guessed calendar policy.

## Religiously neutral future presentation and named reference recommendation

The owner profile remains **religiously neutral**, superseding the earlier idea
of assigning a first Smarta profile to the user. Future verified festival output
should show named Smarta and Vaishnava dates in **one consolidated reminder** when
different; when equal, one date labelled as shared. Preserve both source/profile
identities; different dates must not automatically create two deliveries. Choosing
one consolidated notification time/dedup identity is later integration work.
No festival rule or consolidated reminder is implemented now.

Recommended specifically named Vaishnava comparison profile: **ISKCON / Gaudiya
Vaishnava, GBC Calendar Committee GCal 11**, paired with **Drik Panchang New Delhi
Smartha** as a separately labelled Smarta reference. This is a recommendation,
not “all Vaishnavas,” not an owner sampradaya, and not automatic authority for every
festival. Other Vaishnava traditions can disagree and require their own profiles.

Evidence and reproducibility path:

- [GBC's 2026 resolutions](https://gbc.iskcon.org/gbc-resolutions/resolutions-2026/)
  identify its Vaisnava Calendar Committee.
- [VaisnavaCalendar's GCal 11 notice](https://www.vaisnavacalendar.info/gcal11)
  says its exports use GCal 11, but explicitly disclaims being run/sponsored by
  the GBC committee. Treat that as publisher attestation, not independently
  verified current executable/version. Its 2012 notice is not proof of 2026 build.
- The [2026 text-export index](https://www.vaisnavacalendar.info/calendar-file-downloads/txt-calendar-files-2026)
  lists Delhi. The linked export was inaccessible through the research tool;
  no file, dates, version digest or settings have been validated. Future reference
  intake must pin the actual GCal build, location, timezone, ayanamsa/sunrise and
  rule options, then compare exported dates with a separately reviewed publisher.
- [Drik's own Ekadashi listing](https://www.drikpanchang.com/vrats/ekadashidates.html?year=2026&geoname-id=1261481)
  distinguishes Smartha and Vaishnava observances. A Drik ISKCON page alone is
  not an independent-publisher cross-check of Drik Smartha calculations.

GCal implementation copying, execution, licensing acceptance and festival logic
are out of this prototype. Independent publisher references are not necessarily
independent ephemerides; discrepancy provenance must remain explicit.

## Measured resources and next review

Recorded experiment: 1.154 seconds wall time and 1.152 seconds CPU **after Python
astronomy imports**, including 0.026 seconds kernel/data validation/loading.
Computing all 371 2026 tithi transitions took 0.305 seconds. Peak process RSS was
76,948 KiB (75.14 MiB), including imports; maximum root bracket was 0.041199 seconds.
One-thread BLAS, Linux 512 MiB address-space limit and 60-second CPU limit applied.
This is a development-host measurement, not an India-VPS benchmark, total cold
interpreter startup, service capacity or multi-user production guarantee.

Numerical output is deterministic for identical inputs/profile; resource metrics
vary. Dates solved from different brackets can differ by less than 0.05 seconds;
no subsecond physical accuracy claim follows. Saved JSON intentionally retains
metrics as observed, not asserted deterministic constants.

Next review should resolve the two tithi discrepancies, obtain a fully matched
Delhi sunrise reference, and validate one exact Lahiri convention against pinned
independent epoch tables before named-month/annual-rule work. Keep unsupported
paths blocked. Review the proposed Gaudiya/Smartha reference pairing without
assigning an owner religion. This checkpoint stops; do not begin persistent
scheduling, migrations, reminder integration or festival rules without further review.

No unrelated tests, Docker, DB connection, private backup/manifest search, n8n
change, Telegram send, production access, deployment or merge occurred. Public
package/data acquisition and reference research were the only network operations;
no runtime credentials were used. 2B remains blocked and production reconciliation
and resend/reset remain disabled.
