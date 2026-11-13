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
| P5: 2F Hindu Panchang | No adopted source/engine or fixture suite; no completion claim | Owner chooses calculation/reference source, tradition and geographic parameters before engine/schema commitment. Define sunrise/day-boundary, tithi/paksha/month, amanta/purnimanta, adhika/kshaya, skipped/repeated tithi and observance policy. Compare versioned Delhi reference fixtures across ordinary, transition and leap-month cases; generate stable occurrences with overrides/conflicts/explicit approvals and deduplicated reminders. Investigate public sources only when beginning this task. |
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
host/disk/durable restore and adopted workflow acceptance. The local test-only
checkpoint awaits owner commit because Git metadata is read-only;
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

Pending 2D targeted evidence: full public API weekly/yearly interval and year-boundary
fixtures, multi-selector monthly/yearly combinations, and approved series rule
changes with existing overrides/future reminder materialization. Trusted managed-v2
application/workflow adoption remains tied to 2B. The 730-day default/3660-day
maximum conflict horizon and unsupported overnight schedules are current design
limits. No new architecture decision was required by this checkpoint.

Remaining 2E/2G: supervision/clock and broader outage/restore rehearsal, reviewed
source adoption and real operator authority/identity procedures before any
production enablement. Keep production reconciliation disabled and no resend/reset.
