# Milestone 2 completion plan

Owner decision, 2026-11-13: complete ALL Milestone 2, including Hindu Panchang
scheduling and operational acceptance, before Adhyayan, Arogya, Atma-Chintan,
Vittiya or another orchestrator. Deployment and production access remain gated.
PR #1 merged into main at f3db2ff600dbb417e8bd2c553aad5388697cbd9e; its 429
quarantine fix is included. Prior acceptance is evidence, not permission to rerun
live Telegram or touch production.
Track remaining work in [GitHub issue #2](https://github.com/vasu1765/dincharya-ai/issues/2).

| Priority | Scope and source review | Acceptance criteria / gates |
| --- | --- | --- |
| P0: establish branch | Synchronize main, preserve work; new development/m2-recovery-acceptance | Record upstream merge SHA and clean base; retain existing work; no Git permission bypass. |
| P1: 2E acknowledgement failures | Completed at 120b28a: sanitized finish failures and batch-abort coverage | Normalize finish exceptions/lease loss to sanitized DeliveryUncertain, one transport/finish call, abort remaining batch; synthetic tests for sent/rejected/unknown outcomes, no automatic resend. Completed focused foundation; preserve the no-replay contract. |
| P2: 2D compatibility and adversarial acceptance | 0001/0003 and focused SQL cover recurrence, D10 coexistence/boundaries and the requested adversarial API matrix | Synthetic tests prove old decision dispatch remains functional, cannot bypass managed snapshots/approval or mutate in-flight sends; malformed selectors/bounds reject atomically; occurrence/series edits preserve identity and sent history. Add corrective migrations only when a failure requires them. |
| P3: 2E recovery and receipts | 0002/0004 cover retries, claims and atomic nullable receipts; read-only inspection and owner-approved synthetic reconciliation implemented; production actions disabled | Cover recovery at/outside lookback, lease expiry, stale ack, cancelled/replanned work, restart and duplicate suppression; no blind resend after ambiguous acceptance. Add nullable chat/message receipt with lease-checked atomic acknowledgement and legacy compatibility, then explicit operator reconciliation audit tests. Further live tests need new approval. |
| P4: 2B reproducible source | baseline/ and workflows/ contain guidance only; native/Code source provenance gates remain | Obtain exact missing manifest path, never search backups; hash-bound reviewed schema and current/published workflow provenance; decide adopted vs archived items, preserve Code/state bytes; owner approval before private-source promotion or execution. Prove clean synthetic reconstruction from reviewed source. |
| P5: 2F Hindu Panchang | Phase 1 pushed at 9524757; isolated Skyfield feasibility implemented, incomplete for scheduling; storage/festival integration still gated | Owner chooses calculation/reference source, tradition and geographic parameters before engine/schema commitment. Define sunrise/day-boundary, tithi/paksha/month, amanta/purnimanta, adhika/kshaya, skipped/repeated tithi and observance policy. Compare versioned Delhi reference fixtures across ordinary, transition and leap-month cases; generate stable occurrences with overrides/conflicts/explicit approvals and deduplicated reminders. See M2F_PANCHANG_DESIGN.md for sources, proposed phases and owner decisions; isolated prototype dependencies approved; no migration or persistent integration. |
| P6: 2G operational acceptance | Existing tests are disposable; production readiness is not established | Least-privilege roles, webhook auth, pinned dependencies/images, supervision, redacted logs, health and backlog visibility, restore rehearsal, migration/rollback and recovery runbooks all validated in isolated synthetic environment. Review diff/evidence and obtain explicit owner approval before production access, cutover or deployment. |

P0/P1 are committed (P1 at `120b28a`); D10/recovery is pushed at `db87193`;
P2 adversarial and P3 nullable receipt/atomic acknowledgement evidence is pushed
at `d987b69`. Existing evidence is retained without another live Telegram or full
integration run. See [receipt/adversarial results](M2_RECEIPTS_ADVERSARIAL_RESULTS.md).

The owner approved only isolated synthetic **record confirmed already-delivered**
reconciliation. Migration 0005/API and focused tests, committed at `3d46d8e`,
implement trusted DB identity, independent destination pins, immutable positive evidence and explicit
expiring permits, fresh row versions/locks, atomic append-only audit, scoped
worker privileges and idempotent replay. Concurrency, failure/rollback, duplicate
and privilege acceptance passed. Resume review added a post-lock permit-expiry
check and secret-safe synthetic logging; only its new runtime regression and
seven affected offline checks were run. See [evidence](M2_RECONCILIATION_RESULTS.md)
and [design](RECONCILIATION_DESIGN.md). Production reconciliation and all resend/
reset operations remain disabled. Real evidence authority/provisioning and
production rollout remain separately reviewed owner gates. Full 2D/2E closure,
source adoption, Panchang and operational acceptance remain open. The new
controlled-clock worker reconnect/postmaster crash-recovery matrix passed with
SCRAM/ACL/logging boundaries preserved; prior accepted suites were not rerun.
See [restart/outage evidence and 2D gap matrix](M2_RESTART_RECOVERY_RESULTS.md).
Remaining recovery work is operational: gateway supervision, wall-clock policy,
host/disk/durable restore and adopted workflow acceptance. Restart/outage acceptance
is pushed at `ff6198d`; 2D recurrence API acceptance is pushed at `cb6fdd7`.
2F design is pushed at `9524757`; the current isolated feasibility checkpoint awaits owner review/commit; Git metadata is read-only;
[handoff](HANDOFF.md) contains the exact safe-file commands.

2B, 2D, 2E, 2F and operational acceptance must each have reviewed evidence and
closed remaining gaps before Milestone 2 is complete. Passing one reminder is not
the milestone exit criterion. Keep 2C's passed synthetic scope; do not rerun it
without a relevant functional change. Checksum-corruption rejection remains a
selective migration acceptance gap; do not repeat unrelated integrations for it.

Each implementation task gets a focused branch/PR with source tests and sanitized
evidence; do not merge into main autonomously. Architecture/provider and sensitive
source decisions are owner gates. Routine fixes and focused verification proceed
within approved scope. These acceptance criteria are a plan, not passed results.


## Current 2D/2E exit status after restart acceptance

Satisfied in covered synthetic cases: 2D approval/requester authorization,
event/rule/override staleness, conflict rollback and decision races; D10 legacy/
managed transition boundaries; occurrence overrides/removal and sent-history
preservation. 2E lookback/backoff/lease edges, stale acknowledgements, cancellation/
replanning, duplicate suppression, nullable receipts, synthetic audited resolution
and now committed-state/postmaster crash recovery are verified. See the linked
results matrix for evidence scope; this is not full milestone closure.

The outstanding 2D targeted database/API matrix now passed: weekly/yearly
intervals and year transitions, multi-selector monthly/yearly combinations,
invalid dates/leap/century behavior and inclusive bounds through proposal/approval/
occurrence APIs. Approved series edits over exceptions/cancellations/future
reminders preserve stable identities and sent/uncertain history; explicit
conflict approval and stale-decision rejection passed. No corrective migration
was needed. See [complete 2D matrix](M2D_RECURRENCE_ACCEPTANCE.md).

Full trusted managed-v2 application/workflow integration remains blocked by 2B
reviewed source adoption. The smallest next 2B action is the exact original
provenance manifest path and owner authorization to read that file alone. The
owner confirmed the path is unknown and no private search/referenced-artifact
access is authorized. Do not recreate or substitute a manifest without approval.
Repository-only validator-contract review, synthetic test-gap review and adoption
checklist preparation can proceed without private inputs; they cannot unblock
provenance validation. No referenced artifact is implicitly authorized.
The 730-day default/3660-day maximum conflict horizon, Asia/Kolkata model and
unsupported overnight schedules are existing design limits, not failed cases.
No new architecture decision was required by this acceptance checkpoint.

Remaining 2E/2G: supervision/clock and broader outage/restore rehearsal, reviewed
source adoption and real operator authority/identity procedures before any
production enablement. Keep production reconciliation disabled and no resend/reset.


## 2F Phase 1 design checkpoint

Owner authorized public research, requirements and design only. The
[Panchang design](M2F_PANCHANG_DESIGN.md) compares Skyfield/local JPL, Swiss/Python
bindings, Astronomy Engine and existing Panchang implementations; PAC/Drik/
mypanchang are references with distinct convention/lineage limitations. Research
facts, publisher claims, recommendations and unknowns are separated. No engine
accuracy, runtime or fixture acceptance is claimed.

Proposed order: F2 personal annual/generic monthly tithi with offline astronomy
and independent fixtures; F3 individually verified observance profiles for
Ekadashi, Ram Navami, Janmashtami and Diwali; F4 approved identity/notification-slot
storage and n8n/gateway integration/acceptance. No n8n replacement. Full required
advance/reminder slot support must pass before 2F closure; existing one-row-per-
event/date delivery is not a drop-in multi-reminder API.

Owner approval before implementation: engine/license and pinned data strategy;
Delhi location/sunrise/ayanamsa profile with Purnimanta default and explicit Amanta;
skipped/repeated/intercalary personal policies; ritual authority/tradition; stable
logical identities and staged additive reminder jobs. The design's six numbered
questions remain unresolved, not accepted decisions. 2B provenance remains blocked;
2F research does not authorize private capture/adoption or live tests. No engine,
migration, Telegram operation, deployment or merge in this phase.


## 2F isolated feasibility checkpoint after owner authorization

D14 authorizes the standalone offline Skyfield/DE440s prototype only. See
[M2F_FEASIBILITY_RESULTS.md](M2F_FEASIBILITY_RESULTS.md): 11 focused tests passed,
three NASA phase comparisons within the unchanged 60-second threshold and two
Drik tithi endpoint discrepancies about 86/76 seconds still outside it. One rounded
sunrise reference is numerically close but metadata/model matching is incomplete.
A year of 371 transitions took about 0.305 seconds, measured peak RSS 75.14 MiB;
these are host measurements, not VPS or physical timing-accuracy guarantees.

Physical Amanta/Purnimanta bounds and known intercalary-period sensitivity are
investigated, but exact Lahiri and named-month/exceptional conversion remain
unsupported. Annual birthdays/anniversaries cannot yield guessed dates; generic
monthly preview handles first repeated sunrise/skipped-tithi review experimentally.
No scheduling integration follows from focused-test success; CLI release gate is
incomplete. Next review: resolve independent timing differences, match sunrise
metadata and validate an exact ayanamsa against independent epoch tables.

The owner is religiously neutral: future supported festivals should consolidate
labelled Smarta/Vaishnava dates in one reminder when different. Proposed Vaishnava
reference is ISKCON/Gaudiya GBC Calendar Committee GCal 11 alongside Drik New Delhi
Smartha; current exports/build/settings remain unverified. No festival rule,
persistent schema/identity/slot/notification integration is authorized now. n8n
and existing approval/lease/receipt/quarantine safeguards remain unchanged. Stop
at isolated feasibility; 2B/private access and production remain blocked/gated.
