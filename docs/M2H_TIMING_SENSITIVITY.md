# Cycle 1 — recorded astronomical timing sensitivity (2026-11-14)

**Evidence-only analysis; no new astronomy execution or threshold change.** See [Cycle 1 plan](M2H_CYCLE1_ACCURACY.md) and [issue #3](https://github.com/vasu1765/dincharya-ai/issues/3).

## Sources and selection

Existing immutable result files:
- `prototypes/panchang/feasibility-results.json`: five original `comparisons` (apparent/true-date baseline).
- `prototypes/panchang/validation-results.json`: six `additional_transitions`; **exclude** the nine `controlled_conventions` alternatives from the primary comparison denominator because these are deliberate re-computations of the same events under different hypotheses.
- `prototypes/panchang/recurrence-results.json`: two `new_timing_diagnostics`.

These are **13 recorded source comparisons**, not 13 independent astronomical events: NASA/PAC and Drik/Himalayan rows can describe the same physical boundary with different publishers. All are minute-precision published times, not sub-second truth. This is a descriptive threshold sensitivity calculation, not a statistical accuracy certification. The existing 60-second gate remains unchanged.

| Source | Published instant | Signed residual (seconds) | 60 s | 90 s | 120 s |
| --- | --- | ---: | --- | --- | --- |
| NASA phases | 2023-07-17 18:32 UTC | -9.805318 | pass | pass | pass |
| NASA phases | 2023-08-01 18:31 UTC | +40.319821 | pass | pass | pass |
| NASA phases | 2023-08-16 09:38 UTC | +11.260972 | pass | pass | pass |
| Drik Ekadashi | 2026-01-13 15:17 IST | +85.885600 | **fail** | pass | pass |
| Drik Ekadashi | 2026-01-14 17:52 IST | +75.668324 | **fail** | pass | pass |
| Himalayan Academy | 2026-01-13 15:21 IST | -154.138177 | **fail** | **fail** | **fail** |
| Himalayan Academy | 2026-01-14 17:53 IST | +15.655530 | pass | pass | pass |
| USNO | 2026-01-18 19:52 UTC | -1.071151 | pass | pass | pass |
| IMD PAC | 2023-07-18 00:02 IST | -9.805318 | pass | pass | pass |
| IMD PAC | 2023-07-19 02:10 IST | +23.208610 | pass | pass | pass |
| IMD PAC | 2023-08-16 15:08 IST | +11.260972 | pass | pass | pass |
| Drik 2026 | 2026-03-27 10:06 IST | +82.479851 | **fail** | pass | pass |
| Panchangam 2026 | 2026-03-27 10:07 IST | +22.494496 | pass | pass | pass |

## Sensitivity summary

| Proposed timing diagnostic | Passing recorded comparisons | Failing recorded comparisons |
| --- | ---: | ---: |
| 60 seconds (current) | 9 / 13 | 4 / 13 |
| 90 seconds (hypothetical) | 12 / 13 | 1 / 13 |
| 120 seconds (hypothetical) | 12 / 13 | 1 / 13 |

All 13 values are taken directly from the existing JSON files; a pass means `abs(delta_seconds) <= threshold`. No tolerance, fixture, calculation, reference timestamp or production configuration was changed. This is **not** a recommendation to automatically adopt 90 seconds.

## Important interpretation

- The Himalayan Academy January 13 residual of -154.138177 s remains outside even 120 seconds. The Drik reference for that same tithi boundary differs in its published time; publisher conventions and/or rounding need direct reconciliation.
- For March 27, 2026, Drik and Panchangam published boundaries one minute apart; the same calculation therefore has +82.479851 s versus +22.494496 s residuals. This demonstrates **source-dependent comparison outcomes**, not proof that either publication is wrong.
- The previously attempted nine position/frame hypotheses did not jointly resolve the original Drik failures. Treat the original 60-second gate as a diagnostic rather than an independently certified physical error bound.
- The 300-second research sunrise guard is **separate** from the timing threshold. Neither a 90-second nor a 120-second tolerance certifies near-sunrise date selection. Cross-source civil-date checks and fail-closed behavior remain mandatory.
- No date-selection analysis has been run in this checkpoint; there is no claim of verified annual recurrence, festival observance or release readiness.

## Next focused work

1. Inspect exact original reference provenance and compare publishers' time conventions, coordinate/location profiles and precision, without changing accepted evidence.
2. Add a deterministic regression test/report generator for the 13 recorded rows, with explicit exclusion of alternative frame/position hypotheses.
3. Compare computed Delhi sunrise and tithi boundary for each relevant **civil-date selection** case; withhold conflicting or within-guard results.
4. Produce a decision matrix: explained discrepancy / independent date agreement / near-sunrise risk / supported or withheld; request owner approval before adopting any threshold or calendar engine.
