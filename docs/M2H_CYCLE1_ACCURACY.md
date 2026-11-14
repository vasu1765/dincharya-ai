# Milestone 2, Cycle 1 Panchang accuracy review

**Owner-approved reference policy. Production lunar scheduling stays disabled.** Review scope is
[issue #3](https://github.com/vasu1765/dincharya-ai/issues/3). The comparison
baseline is commit `67dc6a1b16d1208d389ac6f3201cc7d9b6ee8ba4`.

## Timing accuracy

**Conclusion.** The owner adopted an inclusive 90-second publisher-display
diagnostic on 14 November 2026. Drik Panchang New Delhi is primary for civil
dates and IMD PAC is secondary for corroboration. Himalayan Academy remains
historical evidence outside the primary denominator. JPL Horizons reproduced
all eight distinct crossings behind the 13 rows. The diagnostic does not
quantify astronomical uncertainty.

Recomputed all 13 signed residuals using the pinned Skyfield 1.55 environment,
DE440s kernel and repository inputs. All 13 matched the stored values to the
recorded precision. The calculation uses apparent geocentric Sun and Moon
longitudes in the true ecliptic/equinox of date. Tithi crossings are multiples of
12° in Moon minus Sun longitude. A common ayanamsa cancels in this subtraction.
The existing Lahiri hypothesis is relevant to solar sign ingress and month
naming. The solver brackets crossings to 0.05 seconds or better. That numerical
precision does not measure accuracy against a publisher.

| Diagnostic | Pass | Fail |
| --- | ---: | ---: |
| 60 seconds (historical) | 9 | 4 |
| 90 seconds (current diagnostic) | 12 | 1 |
| 120 seconds (hypothetical) | 12 | 1 |

### Full comparison times and displayed-minute precision

| Reference | Published time (IST) | Calculated crossing (IST) | Calculated − published |
| --- | --- | --- | ---: |
| NASA phases | 2023-07-18 00:02 | 2023-07-18 00:01:50.194 | -9.805 s |
| NASA phases | 2023-08-02 00:01 | 2023-08-02 00:01:40.319 | +40.320 s |
| NASA phases | 2023-08-16 15:08 | 2023-08-16 15:08:11.260 | +11.261 s |
| Drik Ekadashi | 2026-01-13 15:17 | 2026-01-13 15:18:25.885 | +85.886 s |
| Drik Ekadashi | 2026-01-14 17:52 | 2026-01-14 17:53:15.668 | +75.668 s |
| Himalayan Academy | 2026-01-13 15:21 | 2026-01-13 15:18:25.861 | -154.138 s |
| Himalayan Academy | 2026-01-14 17:53 | 2026-01-14 17:53:15.655 | +15.656 s |
| USNO | 2026-01-19 01:22 | 2026-01-19 01:21:58.928 | -1.071 s |
| IMD PAC | 2023-07-18 00:02 | 2023-07-18 00:01:50.194 | -9.805 s |
| IMD PAC | 2023-07-19 02:10 | 2023-07-19 02:10:23.208 | +23.209 s |
| IMD PAC | 2023-08-16 15:08 | 2023-08-16 15:08:11.260 | +11.261 s |
| Drik daily | 2026-03-27 10:06 | 2026-03-27 10:07:22.479 | +82.480 s |
| Panchangam.org | 2026-03-27 10:07 | 2026-03-27 10:07:22.494 | +22.494 s |

All timestamps above are **Asia/Kolkata (IST)** for consistent comparison, including NASA and USNO references originally published in UTC. Published references are reproduced at their **displayed minute**, not asserted to mean exactly zero seconds. Calculated crossings show milliseconds solely to make the solver output and residuals auditable; those digits **do not imply millisecond external accuracy**. Same-event cross-source comparisons (such as NASA/IMD PAC, Drik/Himalayan, and Drik/Panchangam.org) are not independent event samples. Source records remain unchanged.

### Publisher methods and display evidence

| Source | Verified convention | Remaining uncertainty |
| --- | --- | --- |
| Drik Panchang | The [New Delhi Ekadashi listing](https://www.drikpanchang.com/vrats/ekadashidates.html?year=2026&geoname-id=1261481) shows whole-minute starts and ends. Its [timing FAQ](https://www.drikpanchang.com/faq/faq-ans1.html?lang=en) defines the daily tithi time as the end of the tithi and illustrates a seconds-bearing display. It uses local time and documents clock and sunrise settings. The captured Delhi page labels Lahiri. | The settings and FAQ do not document nearest-minute rounding or truncation for these pages. The exact ephemeris, apparent/geometric longitude flags and endpoint solver for the fixture pages could not be verified. Do not infer a seconds-bearing version of these rows from the FAQ example. |
| Himalayan Academy / Gurudeva Panchang | Visually checked PDF page 38 of the [New Delhi 2025–26 edition](https://www.minimela.com/wp-content/uploads/panchangam/2025-2026/world/new_delhi_india.pdf). It labels the January 13 and 14 endpoints Dashami 3:21 PM and Ekadashi 5:53 PM respectively. The footer specifies standard time and a New Delhi calculation dated December 20, 2023. Both sunrises print 7:15 AM. The [publisher history](https://hheonline.org/funds/fund_84.html) describes 4D software used to generate calendars for individual cities. | The 4D platform does not identify its astronomical algorithms. No published rounding rule, kernel, coordinate/correction flags or exact horizon definition was found for this edition. |
| IMD Positional Astronomy Centre | The [1945 SE English edition](https://packolkata.imd.gov.in/download/EnglishRP2324.zip), printed pp. v–vii, defines tithi by 12° increments in Moon–Sun longitude and explicitly calls the ending times geocentric and valid anywhere after time-zone conversion. It prints hours and minutes in IST. The day headings follow central-station sunrise, with 24+ hour rollover. Directly rechecked PDF pp. 51 and 59: 24:02, 26:10 and 15:08. | Neither the edition's explanation nor the [PAC public explanation](https://packolkata.imd.gov.in/panchang/en/explanation) establishes how the last displayed minute is rounded or specifies the exact tithi ephemeris/correction flags. All three rows fit nearest-minute rounding on this sample. That observation does not establish a rule. |

The Drik/Himalayan January 13 printed times differ by 240 seconds. Even allowing
each publisher to use either nearest-minute rounding or flooring, the two
possible displayed-time intervals are at least 150 seconds apart. On March 27
[Drik](https://www.drikpanchang.com/panchang/day-panchang.html?date=27%2F03%2F2026&geoname-id=1261481&time-format=12hour)
and [Panchangam.org](https://hindi.panchangam.org/dailypanchangam.php?date=2026-03-27)
have printed intervals that can overlap under mixed conventions. The calculated
crossing lies beyond Drik's interval under both hypotheses.
The NASA GSFC [phase table](https://eclipse.gsfc.nasa.gov/phase/phase2001gmt.html)
credits Espenak's Meeus-based calculations. Its August 2023 full-moon row is
compatible with flooring for the checked crossing, but its July 2023 new-moon
row is not. Do not assign a uniform display policy from these observations.

### Independent astronomical check

Queried [JPL Horizons](https://ssd-api.jpl.nasa.gov/doc/horizons.html) for the
Sun (10) and Moon (301) from Earth's geocenter (500@399), with observer quantity
31 (airless apparent ecliptic-of-date longitude, IAU76/80), extra precision,
UTC and DE441 for both targets. At two UTC samples 60 seconds apart, unwrap
Moon minus Sun around the relevant multiple of 12°. Require a negative-to-
positive crossing and linearly interpolate the signed differences. The
[captured coordinates](../tests/panchang/fixtures/horizons-de441-transitions.json)
include the eight comparison events plus two sunrise cases. The offline
regression derives the crossings from those coordinates and reruns the
pinned Skyfield calculation when the public kernel is configured.

| Horizons crossing (IST) | Entering tithi ordinal | Use |
| --- | ---: | --- |
| 2023-07-18 00:01:50.180 | 1 | NASA and PAC |
| 2023-07-19 02:10:23.192 | 2 | PAC |
| 2023-08-02 00:01:40.299 | 16 | NASA |
| 2023-08-16 15:08:11.245 | 1 | NASA and PAC |
| 2024-05-01 05:46:31.704 | 23 | Delhi near-guard case |
| 2026-01-13 15:18:25.851 | 26 | Drik and Himalayan Academy |
| 2026-01-14 17:53:15.638 | 27 | Drik and Himalayan Academy |
| 2026-01-19 01:21:58.918 | 1 | USNO |
| 2026-03-27 10:07:22.466 | 10 | Drik and Panchangam.org |
| 2026-06-30 05:26:41.190 | 16 | Delhi sunrise split |

The maximum difference across all 13 stored calculations was 0.035 seconds.
The 0.05-second Skyfield bracket and the short Horizons interpolation both
contribute numerical precision limits. Horizons independently evaluates the
coordinates outside Skyfield and uses a slightly different reference ecliptic.
[DE440 and DE441](https://ssd.jpl.nasa.gov/doc/de440_de441.html) were fitted to the
same observations, so agreement cannot establish independent observational truth
or an absolute sub-second error bound. As a separate sensitivity check, Swiss
Ephemeris 2.10.03 through pyswisseph 2.10.3.2 with explicit
[analytic Moshier mode](https://www.astro.com/swisseph/swisseph.htm) reproduced
the ten events within 3.9 seconds of Horizons. This optional check used
`swe.calc` in TT (UTC + 69.184 s for these dates), geocentric apparent tropical
longitudes, and a signed crossing bisected over UTC offsets −60 to +120 seconds
from each fixture start. It adds no project dependency.

A common ayanamsa applied to both longitudes cancels. UTC/UT1 differs by less
than one second for these modern dates. Neither explains these minute-scale
residuals. Different ephemerides, ecliptic definitions, aberration/light-time
choices, geometric versus apparent positions and geocentric versus topocentric
coordinates can alter the crossing. Day roster, sunrise and month naming are
separate calendar conventions. The prior nine coordinate hypotheses did not
jointly explain the January Drik rows. The publisher-side causes remain
unresolved. The matched astronomical calculations make a minute-scale solver
defect unlikely for these events.

### Precision-aware diagnostics

For a published minute `P`, model the underlying publisher time as
`P + [−30, +30] s` for nearest-minute rounding or `P + [0, +60] s` for flooring.
Closed endpoints conservatively cover tie rules. With either convention
plausible, use their union `P + [−30, +60] s` for **sensitivity only**.
An undocumented rule stays unknown. The union is neither a guarantee about the
publisher's time nor an estimate of physical error.

For a hypothetical tolerance, classify the calculation as **within** when
every instant in the interval is within tolerance, **outside** when every
instant is farther away, and **indeterminate** otherwise.

| Display hypothesis | 60 s (within / indeterminate / outside) | 90 s | 120 s |
| --- | ---: | ---: | ---: |
| Nearest minute | 8 / 4 / 1 | 9 / 3 / 1 | 12 / 0 / 1 |
| Floor to minute | 6 / 6 / 1 | 12 / 0 / 1 | 12 / 0 / 1 |
| Either of those two | 5 / 7 / 1 | 9 / 3 / 1 | 12 / 0 / 1 |

Under either display rule, the three Drik endpoints lie at least 25.9, 15.7
and 22.5 seconds outside their conditional intervals (Jan 13, Jan 14 and
Mar 27 respectively). Himalayan January 13 lies at least 124.1 seconds
outside. The raw median absolute residual was 22.495 seconds and the maximum
154.138 seconds. The [original sensitivity matrix](M2H_TIMING_SENSITIVITY.md)
and fixture bytes remain the historical record. These counts describe 13
comparisons, not 13 independent events.

The adopted profile uses three separate checks:

1. Compare the apparent geocentric crossing against a higher-precision
   reference with aligned event, time scale and frame. Record ephemeris,
   solver/interpolation and frame uncertainties. The current 0.1-second test
   bound is a regression check for these pinned samples only. Broader
   validation would need a representative event panel and a separately justified
   numerical tolerance.
2. Compare each publication against its documented display interval and record
   source disagreement separately. Unknown display rules stay unresolved,
   with conditional analysis labelled as such. Compare the same tithi endpoint,
   civil rollover and location-specific label before drawing conclusions.
3. Check Delhi calendar policy using adjacent sunrises and the 300-second
   guard. For credible sunrise interval `[Smin, Smax]` and transition interval
   `[Tmin, Tmax]`, inspect `[Smin − Tmax, Smax − Tmin]`. Withhold if it touches
   `[−300, +300] s` or credible profiles disagree on the selected date. Keep
   unsupported or unresolved cases withheld.

## Adopted reference profiles

| Profile | Evidence to use | Limits |
| --- | --- | --- |
| Drik Delhi | Geoname 1261481, local IST, day tithi at published local sunrise, and explicitly printed Amanta/Purnimanta labels. Capture dated page, settings where available, minute precision, and local-day rollover. Drik documents upper-edge as its suggested sunrise and also offers middle-limb and elevation options. [Sunrise settings](https://www.drikpanchang.com/panchang/sunrise/panchang-sunrise.html?date=14%2F08%2F2024&time-format=24hour) | Exact dated-page horizon flags, elevation, minute display rule, ephemeris, and tithi frame are unverified. Treat apparent geocentric timing in the fixture as a comparison assumption. |
| IMD PAC Rashtriya Panchang | Dated edition and PDF page, IST including >24h rollover, central station 23°11′N/82°30′E, upper limb with 31′ refraction plus 16′ solar radius. Use published tithi and Amanta labels at the stated time, and ingress references for month validation. [PAC explanation](https://packolkata.imd.gov.in/panchang/en/explanation) | Central station sunrise cannot stand in for Delhi. PAC lunar almanac entries are distinct from the civil solar calendar headings. Purnimanta projected from PAC is inferred. |
| Research calculation | Pinned Skyfield/DE440s, Delhi 28.6139°N/77.2090°E, WGS84 and zero elevation, Asia/Kolkata, upper-limb −50′ and PAC-inspired −47′ sensitivity at the same Delhi coordinates. | Both horizons are model hypotheses. Applying −47′ in Delhi does not recreate the PAC central station or certify Drik equivalence. |

Use Drik for Delhi civil-date comparisons and PAC for Amanta, ingress and
geocentric transition corroboration. PAC central-station sunrise labels cannot
override Delhi labels. The published Himalayan January 13 discrepancy remains
visible. The diagnostic reports Drik **3/3**, PAC **3/3**, Himalayan **1/2**
and other context **5/5** at 90 seconds. The preserved 13-row matrix still
reports all observations. Run `python -B -m prototypes.panchang.reference_policy`
to reproduce the current breakdown.

## Focused Delhi sunrise validation

Signs below are computed sunrise minus transition, in seconds. Positive means
the next tithi has started. Published label checks use each provider's date and
location. Computing an offset to a PAC endpoint is separate from comparing
PAC's own station sunrise.

| Delhi civil date | Published observation | Computed offsets, −50′ / −47′ | Result |
| --- | --- | ---: | --- |
| 2023-12-23 | Drik Ekadashi, sunrise 07:10, endpoint 07:11 IST | −125.945 / −110.701 | Both models agree with the publisher label. Withhold both adjacent tithis. |
| 2024-05-01 | Drik Saptami, sunrise 05:40, endpoint 05:45 IST. PAC 1946 SE p. 32 ends Saptami at 05:47 IST. | −375.609 / −361.272 | Both models select Saptami May 1 in research, and withhold skipped Ashtami. PAC endpoint margins at modelled Delhi dawn are 403.895 / 389.546 s. |
| 2024-08-18 | MyPanchang Chaturdashi, sunrise 05:53:15 IST. Drik's preceding Trayodashi ends at 05:51 IST. | +21.011 / +35.184 | Both match the Chaturdashi observation. Withhold both adjacent tithis. |
| 2025-12-20 | Drik Amavasya, sunrise 07:09, endpoint 07:12 IST | −255.144 / −239.859 | Both match the Amavasya observation. Withhold both adjacent tithis. |
| 2026-06-30 | Drik displays Pratipada. It prints both sunrise and the preceding Purnima endpoint at 05:26 IST. MyPanchang corroborates the printed endpoint minute. | about −12 / +3 | Sunrise hypotheses pick different tithis. Only the −47′ hypothesis matches the Drik date label. Withhold both adjacent tithis. |

Publisher pages for the table:
[December 2023](https://www.drikpanchang.com/malayalam/panchangam/malayalam-day-panchangam.html?date=23%2F12%2F2023&time-format=24plushour),
[May 2024](https://www.drikpanchang.com/tamil/tamil-day-panchangam.html?date=01%2F05%2F2024),
[August 2024 MyPanchang](https://www.mypanchang.com/phppanchang.php?cityhead=&cityname=NewDelhi-India&mn=07&monthtype=0&yr=2024),
[August 2024 Drik](https://www.drikpanchang.com/panchang/tithi/daily/shukla-trayodashi-date-time.html?lang=en&year=2024),
[December 2025](https://www.drikpanchang.com/panchang/day-panchang.html?date=20%2F12%2F2025&lang=en),
[June 30 Drik](https://www.drikpanchang.com/panchang/day-panchang.html?date=30%2F06%2F2026&time-format=12hour),
[June 29 Drik](https://www.drikpanchang.com/panchang/day-panchang.html?date=29%2F06%2F2026&lang=en),
[June 2026 MyPanchang](https://www.mypanchang.com/dinadarshika.php?locid=1273294&month=2026-06).

Keep withholding when the absolute distance is 300 seconds or less. For
example, applying a 90-second boundary shift to the May 1 computed margins
can put the event inside the guard even though its tithi label stays unchanged.
The guarded selector withholds May 1 once the earlier published endpoint
and its possible display offset enter the guard. On June 30, a change of
several seconds can change the label. If credible
profiles disagree or the credible joint sunrise and transition uncertainty
enters the guard, withhold the date for review. Treat this as a release
criterion. The guarded development selector checks both models, direct comparable Delhi
labels where available, and the envelope of matching publisher transition
intervals. The existing research previews retain their historical behaviour.

The disputed January 13, January 14 and March 27 endpoints, including both
publisher minutes and the conditional display intervals above, fall between the
same two Delhi sunrises in both models. The nearest margin across these checks
exceeds 3 h 47 min. The relevant sunrise ordinals progress 25→26 on Jan 13/14,
26→27 on Jan 14/15, and 9→10 on Mar 27/28. Those timing disagreements do not
change the corresponding sunrise assignments. On June 30, the Horizons
boundary at 05:26:41.190 IST falls between 05:26:28.894 and 05:26:44.258 IST.
The −50′ model sees Purnima on both June 29 and 30, then Pratipada July 1.
The −47′ model sees Purnima June 29 and Pratipada on June 30 and July 1.
This can change a first/last sunrise date before the guard is applied.
Both profiles still withhold both adjacent tithis.

The existing panel rerun passed 11/11 selected date rows, both sunrise
hypotheses for each. Its closest boundary was 899.121 seconds away. The month
panel reproduced 47 direct PAC Amanta observations, 47 inferred Purnimanta
projections and five separate direct Purnimanta checks. Existing focused
regressions cover ordinary versus Adhika Shravana and canonical identity across
the intervening Adhika month. May 1 adds direct labels for Amanta Chaitra and
Purnimanta Vaishakha on the same sunrise. Coverage remains uneven across years
and exceptions. Ambiguous repetitions require an explicit first/last choice
even in research. Skipped dates, edge uncertainty, Kshaya and unsupported months
stay withheld. Festivals require separate observance rules and validation.

## Reproduction

Use the exact requirements and the public DE440s file verified against
`prototypes/panchang/ephemeris.json`. The focused runs used Linux Python 3.12.14.
Keep original fixtures and JSON results intact. The regenerated JSON is
disposable and the publisher comparisons above are compact public observations.

```bash
export DINCHARYA_PUBLIC_DE440S=/absolute/path/to/de440s.bsp
export OPENBLAS_NUM_THREADS=1
python -B -m unittest discover -s tests -p test_m2h_timing_evidence.py -v
python -B -m unittest discover -s tests/panchang -p test_cycle1_sunrise.py -v
python -B -m unittest discover -s tests/panchang -p test_recurrence.py -v
python -B -m prototypes.panchang.feasibility --ephemeris "$DINCHARYA_PUBLIC_DE440S"
python -B -m prototypes.panchang.validation --ephemeris "$DINCHARYA_PUBLIC_DE440S"
python -B -m prototypes.panchang.recurrence_validation --ephemeris "$DINCHARYA_PUBLIC_DE440S"
python -B -m prototypes.panchang.coverage_validation --ephemeris "$DINCHARYA_PUBLIC_DE440S"
```

The precision follow-up passed all 29 focused tests (13 timing, four sunrise
and 12 recurrence). Its kernel-free timing run passed 12 tests and skipped the
single kernel-dependent check. The original 23-test checkpoint also ran four
research CLIs, which emitted evidence and exited
with their intentional status 2. Cold annual preview was about 2.9 seconds
and an identical warm call about 0.09 milliseconds on this workspace profile.
These are host observations with no performance guarantee.

## Cycle 2 Telegram contract

Accept English, Hindi and Hinglish free text and retain slash commands.
Parse into a draft intent with event title, date or recurrence, time, timezone
and applicable lunar choices. Clarify missing or ambiguous fields, including
birth instant versus sunrise and month convention when needed. Deterministic
validation produces a structured preview with the selected policy, local date,
and reminder time. Withheld or unsupported dates have no approval action.
A Confirm or Cancel button, or equivalent command, binds the authenticated
owner's decision to the exact unexpired preview. Corrections require a new
preview and approval. Only the existing authorized service may persist a
validated approved schedule. Duplicate or stale actions must use the normal
approval safeguards and report status without creating another schedule.
The LLM parses and explains. It has no scheduling or database write authority.

## Release recommendation

The owner approved guarded implementation and testing in development. The
90-second display diagnostic remains independent of the 300-second guard.
Release and production enablement require separate approval and broader
validation. Personal anniversary rules remain separate from festival
observance rules.
