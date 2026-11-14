# Milestone 2, Cycle 1 Panchang accuracy review

**Ready for review. Keep astronomical scheduling disabled.** Review scope is
[issue #3](https://github.com/vasu1765/dincharya-ai/issues/3). The comparison
baseline is commit `67dc6a1b16d1208d389ac6f3201cc7d9b6ee8ba4`.

## Timing accuracy

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
| 60 seconds (current) | 9 | 4 |
| 90 seconds (hypothetical) | 12 | 1 |
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

**Publication precision matters:** for a truly nearest-minute-rounded publication, the hidden underlying time can be as much as 30 seconds earlier or later than the printed minute. If a publisher always truncates/floors to the minute, the hidden time can fall in the following 60-second interval. These are *conditional examples*, not confirmed policies for Drik, Himalayan Academy, IMD PAC, or the other sources. A printed-minute residual cannot establish absolute astronomical error without a verified publisher display policy and compatible calculation profile. Importantly, such display precision **does not justify automatically adding 30 or 60 seconds to an acceptance threshold**.

For the same January 13 tithi transition, the printed Drik 15:17 and Himalayan 15:21 differ by **240 seconds**; ordinary nearest-minute rounding could account for at most 60 seconds of difference between two displays of an otherwise identical underlying instant. It cannot, by itself, explain their four-minute gap. Their location, ephemeris, apparent/geometric model, event definition, conventions and clock formatting remain to be reconciled. On March 27, the printed Drik 10:06 and Panchangam.org 10:07 differ by 60 seconds, which may arise from their minute display rules or genuine calculation/profile differences; neither explanation is verified.

**Interpret the 60/90/120 table as a raw displayed-minute diagnostic sensitivity table, not as true-error pass rates.** The 90-second threshold would count three additional raw rows as passing, but would not demonstrate that the engine is closer to the underlying true transition. A better follow-up is a precision-aware comparison with confirmed source formatting and an independent higher-precision reference, retaining source-specific uncertainty separately from numerical solver tolerance and from the sunrise date-selection safety guard. Until those checks exist, preserve the raw 60-second diagnostic, the 300-second sunrise withholding guard and disabled personal-lunar scheduling.


Median absolute residual is 22.495 seconds and maximum is 154.138 seconds.
These are 13 publisher comparisons and include overlapping physical events.
The [full sensitivity matrix](M2H_TIMING_SENSITIVITY.md) retains the source records
and signed residuals; the table below additionally shows calculated crossing times. The nine alternative frame/position calculations were
reproduced separately and still did not jointly explain the January Drik results.

| Current failure | Exact source and convention | Finding |
| --- | --- | --- |
| Jan 13, 2026, +85.886 s | [Drik Ekadashi, New Delhi 1261481](https://www.drikpanchang.com/vrats/ekadashidates.html?year=2026&geoname-id=1261481), tithi begins 15:17 IST. [Daily page](https://www.drikpanchang.com/panchang/day-panchang.html?date=13%2F01%2F2026&time-format=24hour) also prints 15:17 and labels Lahiri. | Himalayan prints 15:21. Four minutes exceeds ordinary whole-minute rounding differences. Cause and authority unresolved. |
| Jan 14, 2026, +75.668 s | Same Drik listing, tithi ends 17:52 IST. | Himalayan prints 17:53. Minute publication can contribute uncertainty. Exact rounding and coordinate conventions are unknown. |
| Mar 27, 2026, +82.480 s | [Drik daily page, New Delhi](https://www.drikpanchang.com/panchang/day-panchang.html?date=27%2F03%2F2026&time-format=12hour), Navami ends 10:06 IST. | [Panchangam.org Delhi](https://hindi.panchangam.org/dailypanchangam.php?date=2026-03-27) prints 10:07, residual +22.494 s. The printed minute explains the difference between residuals. Publisher engine lineage and the absolute discrepancy remain unresolved. |
| Jan 13, 2026, −154.138 s | [Himalayan Academy New Delhi 2025–26 PDF](https://minimela.com/wp-content/uploads/panchangam/2025-2026/world/new_delhi_india.pdf), PDF page 38, parsed and provisional, 15:21 interpreted as IST. | It fails all three thresholds. Exact geography, sunrise convention, ayanamsa, engine, and rounding rule are unverified. |

Times are published to whole minutes. The conditional display-precision cases
above mean that raw seconds-level residuals must not be misrepresented as
absolute astronomical errors. With unknown rounding and longitude/frame
settings, increasing the diagnostic threshold would count three additional
unresolved Drik comparisons as passes. The current
diagnostic does not supply an error bound for sunrise selection. No numerical
engine defect was demonstrated by these comparisons. A defect in the evidence
test itself was reproduced and fixed. It keyed by publisher and discarded the
earlier of the two Himalayan rows.

## Reference profiles for owner review

| Profile | Evidence to use | Limits |
| --- | --- | --- |
| Drik Delhi | Geoname 1261481, local IST, day tithi at published local sunrise, and explicitly printed Amanta/Purnimanta labels. Capture dated page, settings where available, minute precision, and local-day rollover. Drik documents upper-edge as its suggested sunrise and also offers middle-limb and elevation options. [Sunrise settings](https://www.drikpanchang.com/panchang/sunrise/panchang-sunrise.html?date=14%2F08%2F2024&time-format=24hour) | Exact dated-page horizon flags, elevation, rounding, ephemeris, and tithi frame are unverified. Treat apparent geocentric timing in the fixture as a comparison assumption. |
| IMD PAC Rashtriya Panchang | Dated edition and PDF page, IST including >24h rollover, central station 23°11′N/82°30′E, upper limb with 31′ refraction plus 16′ solar radius. Use published tithi and Amanta labels at the stated time, and ingress references for month validation. [PAC explanation](https://packolkata.imd.gov.in/panchang/en/explanation) | Central station sunrise cannot stand in for Delhi. PAC lunar almanac entries are distinct from the civil solar calendar headings. Purnimanta projected from PAC is inferred. |
| Research calculation | Pinned Skyfield/DE440s, Delhi 28.6139°N/77.2090°E, WGS84 and zero elevation, Asia/Kolkata, upper-limb −50′ and PAC-inspired −47′ sensitivity at the same Delhi coordinates. | Both horizons are model hypotheses. Applying −47′ in Delhi does not recreate the PAC central station or certify Drik equivalence. |

Proposed use is Drik as a Delhi civil-date comparator and PAC as an independent
publisher for Amanta/ingress/transition corroboration. This requires an owner
review before any reference authority or engine is adopted. Agreement alone
does not establish independent numerical lineage.

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
On June 30, a change of several seconds can change the label. If credible
profiles disagree or the credible joint sunrise and transition uncertainty
enters the guard, withhold the date for review. Treat this as a release
criterion. The current prototype's local guard does not implement a publisher
consensus check or an uncertainty budget.

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

23 focused tests passed. The four research CLIs emitted evidence and exited
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

**No-go for persisted or live personal lunar anniversaries.** Keep offline
research preview and the existing 60-second diagnostic. Require a reviewed
Delhi profile and a defensible explanation or independently justified
disposition of remaining timing failures before reconsidering release. Widening
the timing diagnostic is not justified by raw minute-display residuals alone;
first verify publisher display precision and profiles, then reassess source-aware
accuracy while keeping civil-date safety independent. Festival observance
and any production enablement remain separate approval decisions.
