# Milestone 2F — all-name coverage, logical identity and proposed date gate

Current branch development/m2f-skyfield-feasibility, pushed base
`0a1cae678dc9a00a120a56a703f74a23935bfde2`; entry clean, HEAD/tracking/GitHub
agree, no open PR. This is offline research only, **not calendar-engine or scheduling
adoption**. Git metadata remains read-only; see HANDOFF for explicit owner commands.

## Evidence matrix and what it proves

New [coverage-references.json](../prototypes/panchang/coverage-references.json)
adds evidence without rewriting any accepted fixture or result. Reused the pinned
public PAC1945SE/2023–24 and PAC1946SE/2024–25 ZIP/PDF files outside Git; exact
archive/member hashes are repeated in the new metadata and agree with prior
provenance. Existing pypdf6.1.1 inspected selected daily lunar Tithi parentheses,
Gregorian dates/Julian days and central-station sunrise, not National Calendar or
All-India Nirayana **solar** headings. No new package, ephemeris or bulk web scraper.
The observation instant is one minute after the printed PAC central-station
sunrise, with published tithi ending at least an hour later (or ahoratra). It is
an explicit instant check, **not a Delhi-sunrise/date claim**.

47 directly published Amanta name/paksha/tithi cases match. Both pakshas of all12
names are represented across the two editions. The earlier edition does not cover
Phalguna Krishna in the selected range; the later one does. Do not claim48 cases
or two complete years for every name. Purnimanta projection for these47 cases is
explicitly inferred; it is not a direct PAC Purnimanta table. Five additional
primary-publisher label comparisons directly corroborate the previously missing
Purnimanta names. All99 core comparisons pass (47 direct Amanta +47 inferred
Purnimanta +5 direct Purnimanta). Additional Amanta corroboration in those five
rows is not counted again. Prior month/Adhika/direct reference evidence is retained
separately, not conflated with this new corpus.

| Lunar name | PAC Amanta Shukla | PAC Amanta Krishna | Purnimanta inferred | New Purnimanta direct |
| --- | ---: | ---: | ---: | ---: |
| chaitra | 2 | 2 | 3 | 0 |
| vaishakha | 2 | 2 | 4 | 0 |
| jyeshtha | 2 | 2 | 4 | 1 |
| ashadha | 2 | 2 | 4 | 0 |
| shravana | 2 | 2 | 4 | 0 |
| bhadrapada | 2 | 2 | 4 | 1 |
| ashvina | 2 | 2 | 4 | 1 |
| kartika | 2 | 2 | 4 | 1 |
| margashirsha | 2 | 2 | 4 | 1 |
| pausha | 2 | 2 | 4 | 0 |
| magha | 2 | 2 | 4 | 0 |
| phalguna | 2 | 1 | 4 | 0 |

All12 names now have selected research support in the evaluator; no general
certification of arbitrary years or exceptions follows. All outputs retain
usable_for_scheduling=false. Direct Purnimanta coverage remains uneven (five new
rows mostly Krishna; prior Chaitra/Shravana evidence is separate). Inference is
never relabelled a direct golden. New source details/pages and exact selected
observation instants are in the JSON, with [numeric results](../prototypes/panchang/coverage-results.json).

Official source context was checked2026-11-13:
[PAC daily index](https://packolkata.imd.gov.in/panchang/en/panchang),
[explanation](https://packolkata.imd.gov.in/panchang/en/explanation),
[dated English archives](https://packolkata.imd.gov.in/rashtriya-panchang-english.php).
PAC station is23°11′N/82°30′E; its time notation is IST. Current online index is
2026–27 and its headings are solar calendars, so it was not used as a2023/24
lunar table. Exact archival edition/member/page is used for dated cases.

Direct new Purnimanta corroborations, month/paksha labels only:

- [Drik2024-06-10](https://www.drikpanchang.com/panchang/month-panchang.html?date=10%2F06%2F2024&time-format=12hour),
  New Delhi: Amanta/Purnimanta Jyeshtha, Shukla.
- [Drik2024 Bhadrapada](https://www.drikpanchang.com/festivals/lunar-month/festivals-bhadrapada.html?lang=en&year=2024),
  Amarnath Maharashtra as indexed: August20 northern Bhadrapada Krishna; PAC
  corroborates backing Shravana Krishna. Festival algorithms are not used.
- [AstroSage2023-10-10](https://panchang.astrosage.com/panchang/aajkapanchang?date=10-10-2023&language=en&view=amp),
  New Delhi: Bhadrapada Amanta / Ashwin Purnimanta, Krishna.
- [Drik2023-11-10](https://www.drikpanchang.com/panchang/day-panchang.html?date=10%2F11%2F2023&lang=en),
  Powai as indexed: Ashwina Amanta / Kartika Purnimanta, Krishna.
- [Drik2023-12-10](https://www.drikpanchang.com/panchang/month-panchang.html?date=10%2F12%2F2023&lang=en),
  Hisar as indexed: Kartika Amanta / Margashirsha Purnimanta, Krishna.

These are direct publisher labels observed in primary indexed text, not invented
conversions. Direct fetches had cache misses; raw web hashes/version/engine lineage
are not claimed. Locations differ: labels were tested at explicit instants safely
inside the fortnight, not treated as matching Delhi-sunrise timing. Transliteration
normalization is explicit. PAC PDF extraction is not visual facsimile certification.
All raw documents remain outside Git; fixtures contain small public facts only.

## Logical identity version2, provenance and selection separation

Previous v1 included calculation-profile hash and Gregorian new-moon date. Both
can change after an engine upgrade and could create duplicates. New research v2:

```json
{"version":2,"convention":"purnimanta","month":"chaitra",
 "intercalation":"ordinary","lunation_cycle":324,"paksha":"shukla","tithi":9}
```

Logical identity contains no engine, ephemeris/version, sunrise hypothesis,
selected date or first/last policy. Calculation provenance is a separate object
with profile hash and canonical new-moon date. Selected Gregorian date and selection
policy are separate fields. A future immutable event/series ID must scope this
calendar identity; this is not an approved database key or migration.

The cycle discriminator is a **fixed counting convention**, not a phase calculator:
round the canonical backing new-moon offset from2000-01-06 18:14UTC by fixed
29.530588861-day spacing. Require the solved new moon within3 days of that center;
otherwise reject for reconciliation. The epoch/spacing literals are identity
contract constants, independent of installed ephemeris/ayanamsa. They never assign
month/tithi or generate dates. Tests check consecutive cycle counts in1901,2000,
2023,2099 and numerical shifts across UTC midnight. This removes the old fragile
UTC-date discriminator and its artificial midnight gate. Changing this counting
contract would require an explicit identity migration policy.

Purnimanta canonicalization is retained: ordinary Krishna before Adhika Shravana
anchors to the later ordinary Shravana Shukla lunation; ordinary Shukla after Adhika
uses the same cycle. Adhika's two pakshas share the earlier cycle. Ordinary/Adhika
remain distinct. No Kshaya name or neighbor mapping is invented.

`logical_key` strictly validates v2 fields (no embedded profile/extra keys).
`reconcile_calculations` is an offline comparison only: same logical identities
across profiles remain single rows; changed selected dates are withheld with
calculation_date_disagreement. Duplicate keys, legacy/unknown keys, changed cycles,
names or identity sets reject for explicit review. It never appends new identities
because an engine changed, changes a stored record, resolves delivery or resends.
Callers of any future persistent integration must compare against the existing
ledger; blindly appending a new preview is not a supported upgrade operation.

### Owner approval required before persistence

No records have been migrated. v1 research keys cannot be blindly upgraded: map
them one-to-one against recomputed v2 cycles, reject ambiguous mappings, retain
provenance/history/approval and sent/uncertain receipts, and review changed selected
dates or month labels. If ayanamsa/convention/rule interpretation changes a lunar
label/canonical cycle, require explicit reconciliation/approval rather than quietly
creating a new occurrence. Era/cycle semantics, per-series scoping and v1 mapping
need owner review before any persistent key adoption. They do not block this
requested offline research; no new authorization is needed to review these files.

## Proposed calendar-date acceptance gate

This is a **proposal**, separate from both physical timing diagnostics and
production enablement. All stages must pass or the affected date is withheld:

1. Input/profile: aware instants, supported complete intervals, pinned data and
   explicit Delhi/convention/birth basis/repetition/intercalation policy. Unknown
   model, range or exceptional context fails closed.
2. Identity: unique logical keys, stable cycle correspondence across profiles;
   no silent ledger append/re-key on engine change. Identity disagreements require
   explicit mapping, date disagreements preserve key but withhold selection.
3. Calendar references: compare name/flag/paksha/tithi at stated instants and civil
   selection against independently dated references. Record direct versus inferred
   evidence and location/horizon/time conventions. Central-station sunrise cannot
   certify Delhi. Broad direct Purnimanta/multi-year golden coverage remains pending.
4. Sunrise sensitivity: both pinned hypotheses must agree and candidate sunrise
   must be farther than300 seconds from a solved tithi boundary. Also compare
   credible independent publisher civil dates; if any disagreement changes the
   selected date, investigate or withhold even beyond300 seconds. The guard is a
   conservative research policy, not a certified error bound.
5. Repeated/skipped: default repeated dates need review; explicit first/last must
   be retained independently of identity/window. Skipped tithis have no guessed
   fallback. Adhika selected2023 cases must preserve distinct cycles and ordinary
   split halves. Kshaya/multiple ingress and unvalidated exceptional neighbors are
   expected rejection cases, not calendar-date passes.
6. Personal versus festival: sunrise personal tithi is not a festival algorithm.
   Preserve the2026 March27 personal Navami / March26 Smarta observance distinction;
   do not infer ritual authority or implement festivals. Neutral user profile stays.
7. Release: selected fixture passes do not authorize adoption. Exact independent
   source profiles, broader reference coverage, exception/identity policies and
   explicit owner review remain gates before any scheduling integration.

Confirmed code defect fixed: the old preview loop used120 seconds despite
advertising300. It now applies DATE_GUARD_SECONDS=300. A synthetic sunrise240
seconds after a real transition, with explicit first-date selection, is withheld;
previous120-second logic would select it. Existing astronomical0.1-second/120-second
APIs and every60-second comparison remain unchanged. No tolerance was relaxed.

Deliberately sunrise-sensitive independent evidence: PAC1946SE PDF page32 says
May1,2024 Chaitra Krishna Saptami ends05:47IST. Delhi dawn under the two pinned
hypotheses is05:40:16 /05:40:30, giving403.895 /389.546 seconds of separation.
Both classify Saptami and select May1; PAC station sunrise is not substituted.
This is a geocentric PAC boundary checked against computed Delhi dawn, not a
published matching-profile Delhi sunrise certification. Existing direct Delhi
repeated/skipped fixtures remain; synthetic240-second and profile-induced
civil-date disagreement tests verify withholding where needed.

## Tests, timing and performance

- Seven new focused tests pass (six initial8.563s plus cycle-range1.221s; two
  strengthened guard/midnight tests rerun0.456s). Twelve materially affected
  recurrence tests pass22.265s. The old unsupported-name test was updated to
  assert new support while retaining a restricted-scope fail-closed regression;
  identity tests now assert the logical cycle rather than old provenance dates.
- All47 PAC comparisons,47 inferred Purnimanta comparisons and5 direct new
  Purnimanta comparisons pass. Near-sunrise cases pass under both models.
  Old eight fixture/result files remain byte-for-byte unchanged and hash-checked.
- Original60-second astronomical timing comparisons remain failed where previously
  recorded (+85.886/+75.668s original Drik; new March2026 +82.480s Drik versus
  +22.494s other publisher). They were not rerun or altered. A publisher residual
  without a date change is not automatically a demonstrated calculation defect;
  the cause remains unproven.
- Current cold annual1.991s versus previous recorded2.056s (ratio0.968), warm
  identical request0.000089s, no added month calculations. Month32/preview8/
  sunrise800 bounds retained; complete coverage run7.930s,peak RSS87,424KiB.
  No material regression observed on this host; one sample/no VPS guarantee.
- CLI intentionally exits2 with usable_for_scheduling=false. Same pinned packages,
  DE440s, one-thread BLAS,512MiB/60CPU-second limits and pre-import network guard.
  No old coordinate experiments, unrelated integration, Docker, n8n or live sends.

All12 ordinary names have selected research coverage, but overall calendar gate
remains **incomplete**: uneven direct Purnimanta goldens, exact source horizon/
coordinate matching, broader intercalary/exception and independent epoch evidence.
Kshaya/uncertain boundaries, ambiguous identity mapping and changed selected dates
remain unsupported/withheld. Final persistence/migration, calendar-date policy and
engine adoption require owner approval. No production/private access, DB migration,
2B search, deployment or merge. Stop after this offline checkpoint.
