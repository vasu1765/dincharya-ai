# Cycle 1 — Panchang accuracy investigation and release gates

Status: **in progress — baseline evidence review only**. Issue: [#3](https://github.com/vasu1765/dincharya-ai/issues/3).

## Scope and immutable baseline

This cycle starts from the completed M2G branch. Preserve all prior evidence, original reference bytes, existing 60-second timing diagnostic and 300-second sunrise/date-selection guard. No live lunar scheduling, Telegram sends, production changes, merges, or broadened calendar claims. The previously successful private live Telegram acceptance is not rerun.

## Recorded timing observations (not newly executed)

| Reference | Recorded signed residual | 60 s diagnostic | Hypothetical 90 s | Hypothetical 120 s |
| --- | ---: | --- | --- | --- |
| Drik, Jan 13 2026 Ekadashi boundary | +85.886 s | fail | pass | pass |
| Drik, Jan 14 2026 next boundary | +75.668 s | fail | pass | pass |
| Drik, Mar 27 2026 | +82.480 s | fail | pass | pass |
| Panchangam, Mar 27 2026 | +22.494 s | pass | pass | pass |
| Himalayan Academy (one recorded discrepancy) | 154 s magnitude | fail | fail | fail |

These comparisons are a **descriptive sensitivity table**, not a validated tolerance change. Signed residuals are from existing research documentation; the Himalayan magnitude is recorded without asserting a sign. Other reference rows are not represented here and must be inventoried before any distribution or pass-rate claim. The original 60-second failures remain failures.

Prior research found nine coordinate/frame hypotheses unable to explain both original Drik residuals. Selected PAC ingress/month labels and several numeric boundaries matched, but source profiles, rounding, location and independent publisher lineage remain incompletely resolved. A publisher mismatch alone is not proof of an implementation defect.

## Investigation tasks

1. Inventory exact existing reference fixtures, recorded timestamps, source pages, publication precision, reference location, sidereal/tropical and ayanamsa conventions, coordinate frames and sunrise definitions. Preserve provenance and immutable fixture hashes.
2. Reproduce *focused* residuals without altering baselines or repeating unrelated successful integration suites. Identify whether differences are reproducible numeric bugs, documented convention mismatches, publication rounding, or unresolved.
3. Calculate a complete 60/90/120-second sensitivity matrix across all existing comparable reference rows, with source-by-source residuals and outliers. Do not change assertions or treat widened tolerance as accuracy evidence.
4. Independently validate the **selected civil date** for Delhi under explicitly pinned profile assumptions, especially tithi changes near sunrise. Keep the existing >=300-second research guard; any mismatch in date, source profile or confidence withholds scheduling.
5. Extend directly published multi-year Purnimanta/Amanta and Adhika cases; document repeated/skipped handling. Kshaya, ambiguous exceptional months, unverified annual dates and festival-specific observances remain unsupported until separately validated.
6. Propose a documented reference profile and any justified tolerance change for owner review. A threshold change cannot be approved solely because 90/120 seconds turns failing rows green.
7. Record regression evidence, performance and release/no-release matrix. Distinguish research preview from permitted persistent lunar scheduling.

## Separate Cycle 2 interface contract (design only)

Telegram free text in English/Hindi/Hinglish -> intent/slots with explicit timezone and recurrence -> clarify ambiguities -> deterministic validated preview -> user approval via inline button or command -> authorized persistence -> status/receipt. No LLM direct database writes, approval bypass, implicit event changes or guessing unsupported lunar dates. Keep slash commands as fallback.

## Approval gates

Owner approval is required before adopting a calculation engine/reference authority, changing the numeric timing tolerance or sunrise guard, introducing major architectural/schema changes, enabling general lunar scheduling, accessing production, deployment, or merging main.

## Exit criteria

An evidence-backed report with reproducible residual matrix and date validation; all unsupported cases explicitly fail closed; recommendation for personal lunar recurrence separately from festival observance; tests and reviewed diff; explicit owner go/no-go decision. No claim of Cycle 1 completion from this planning checkpoint.
