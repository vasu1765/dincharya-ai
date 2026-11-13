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
