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
| P4: 2B reproducible source | Owner approved the new [source-review route](M2B_SOURCE_ADOPTION.md) | Review the hash-bound candidate package and reconstruction. Record adoption or archival per artifact. Private source and historical Code execution require separate authorization. |
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
2F design is pushed at `9524757`; prototype research at `6f1f0b7` and timing/range
validation at `452bbcd` are accepted as research only. Month research is pushed at2bd37c0; general offline preview
research now awaits review/commit; Git metadata is read-only;
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

Full trusted managed-v2 application/workflow integration requires 2B artifact
decisions and a reviewed promotion. Proceed through the
[new source-adoption route](M2B_SOURCE_ADOPTION.md). Preserve prior provenance
evidence and take separate authorization for each private input.
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

Owner authorized the isolated in-memory seam after pushed assessment9eaf859.
Current branch development/m2f-memory-contract implements two synthetic personal
series, immutable proposal/approval snapshots and fake ledger/history.29 focused
checks pass; no DB/worker/delivery integration. See
[M2F_MEMORY_CONTRACT.md](M2F_MEMORY_CONTRACT.md) for contract, SQL differences,
readiness and risks. Next PostgreSQL mapping/auth/transaction/locking design and
finite synthetic test plan need separate approval before implementation/execution.
Existing calendar/astronomy validation limits and no-scheduling boundary remain.

The owner is religiously neutral: future supported festivals should consolidate
labelled Smarta/Vaishnava dates in one reminder when different. Proposed Vaishnava
reference is ISKCON/Gaudiya GBC Calendar Committee GCal 11 alongside Drik New Delhi
Smartha; current exports/build/settings remain unverified. No festival rule,
persistent schema/identity/slot/notification integration is authorized now. n8n
and existing approval/lease/receipt/quarantine safeguards remain unchanged. Stop
at isolated feasibility; 2B/private access and production remain blocked/gated.

## Current 2F PostgreSQL implementation checkpoint

Memory contract pushed0304de6 and design81acd6a; owner authorized implementation
on development/m2f-postgres-integration. Additive0006, opt-in Python adapter and
finite T00–T26 runner implement the native once-projection seam with six metadata
records (audit includes approved revisions). See [results](M2F_POSTGRESQL_RESULTS.md).

Offline19 tests pass; database runtime/grammar/ACL/race evidence remains pending.
**Next gate is explicit authorization for isolated PostgreSQL/Docker acceptance**,
not more routine coding approval. No engine adoption, live scheduling or workflow
activation. Advance slots, astronomical acceptance,2B provenance and operational
acceptance remain outstanding; do not begin another orchestrator. Earlier design
and research paragraphs are historical scope records, superseded by D21 only for
this synthetic implementation; production and actual database execution stay gated.

## Current 2F synthetic PostgreSQL acceptance — passed

Owner-authorized T00–T26 passed on development/m2f-postgres-integration, based on
pushed5991138 and additive corrections0007/0008.20 focused offline tests passed;
cleanup and unchanged unrelated container IDs confirmed. See
[actual results](M2F_POSTGRESQL_RESULTS.md). This supersedes the preceding runtime
execution gate for the completed scoped run only. No open synthetic acceptance
failure remains. Preview ingestion, advance slots, astronomical release and full
operational acceptance remain pending; no production or workflow adoption.

## Current 2F synthetic E2E — passed

On development/m2f-synthetic-e2e, the fixture-only n8n request/explicit approvals/
native projection/existing worker/simulated receipt journey passes E01–E05,
including two process/n8n restart cycles, duplicate/history and failure handling.
46 offline tests pass. The older standalone fixture now explicitly initializes
host SCRAM; reviewed digest updated after demonstrated failure. No T00–T26 rerun.
See [evidence and live-test blockers](M2F_SYNTHETIC_E2E_RESULTS.md). Real authenticated
gateway/driver/transport binding, separate private test-bot authorization, validated
calendar adoption, advance slots and operational acceptance remain outstanding.

## Current M2G Telegram application seam — passed in isolation

On development/m2g-telegram-integration, real SDK/psycopg/signed n8n application
passes G01–G04 with Telegram IO simulated and73 focused regressions. Existing
Gregorian scheduler, worker, leases, receipts and history are reused;0009 adds
only owner-scoped status/identity reads. Two service/n8n restarts and gateway SDK
rebuild preserve exact history and unrelated containers. See
[M2G evidence](M2G_TELEGRAM_RESULTS.md) and [prepared private test](M2G_TELEGRAM_ACCEPTANCE.md).
The earlier first-private-test implementation blockers are resolved for fixtures;
next is explicit one-reminder live acceptance authorization and hidden credentials.
General calendar/astronomy, advance slots,2B provenance and wider operational/VPS
acceptance remain gated. No additional orchestrator or deployment authorized.

## M2H Cycle 5 — recurring schedules and notification slots

See the [Cycle 5 development evidence and completion matrix](M2H_CYCLE5_RECURRENCE.md).
Cycle 4 exact-schema acceptance passed under its existing scope. Cycle 5 adds
isolated automatic recurrence and notification selection. Broader calendar
validation, 2B provenance, supervised recovery, cross-cluster restore and
separate release approval remain open.


## Current M2H Cycle 6 checkpoint

Use the [2B source review](M2B_SOURCE_ADOPTION.md) route approved by the owner.
Historical Delhi lookups and Gregorian-event lunar anniversary previews
reuse the guarded annual recurrence service. The [Cycle 6 results and follow-up](M2H_CYCLE6_HISTORICAL.md)
track evidence, the new-migration exact-schema rehearsal and release decisions.

## Current M2H Cycle 7 checkpoint

The focused authorized-schema 0014 run passed with exit 0 in the same disposable
database. The separate synthetic cross-cluster rehearsal passed independently.
Owner decisions for artifact promotion and the bounded private test remain. See the
[release checklist and WSL task](M2H_CYCLE7_RELEASE.md#remaining-release-decisions).
