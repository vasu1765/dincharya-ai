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
| P1: 2E acknowledgement failures | Worker finish failures currently escape raw; six existing worker tests omit DB exceptions | Normalize finish exceptions/lease loss to sanitized DeliveryUncertain, one transport/finish call, abort remaining batch; synthetic tests for sent/rejected/unknown outcomes, no automatic resend. First prepared task. |
| P2: 2D compatibility and adversarial acceptance | 0001 and gregorian.sql cover monthly/leap/ISO week, overrides, stale proposals, conflicts and replay; legacy API coexistence incomplete | Synthetic tests prove old decision dispatch remains functional, cannot bypass managed snapshots/approval or mutate in-flight sends; malformed selectors/bounds reject atomically; occurrence/series edits preserve identity and sent history. Add corrective migrations only when a failure requires them. |
| P3: 2E recovery and receipts | 0002, reminders.sql and PR #1 prove retry cap, concurrent claims and one owner-approved delivery; transport receipts not stored | Cover recovery at/outside lookback, lease expiry, stale ack, cancelled/replanned work, restart and duplicate suppression; no blind resend after ambiguous acceptance. Add nullable chat/message receipt with lease-checked atomic acknowledgement and legacy compatibility, then explicit operator reconciliation audit tests. Further live tests need new approval. |
| P4: 2B reproducible source | baseline/ and workflows/ contain guidance only; native/Code source provenance gates remain | Obtain exact missing manifest path, never search backups; hash-bound reviewed schema and current/published workflow provenance; decide adopted vs archived items, preserve Code/state bytes; owner approval before private-source promotion or execution. Prove clean synthetic reconstruction from reviewed source. |
| P5: 2F Hindu Panchang | No adopted source/engine or fixture suite; no completion claim | Owner chooses calculation/reference source, tradition and geographic parameters before engine/schema commitment. Define sunrise/day-boundary, tithi/paksha/month, amanta/purnimanta, adhika/kshaya, skipped/repeated tithi and observance policy. Compare versioned Delhi reference fixtures across ordinary, transition and leap-month cases; generate stable occurrences with overrides/conflicts/explicit approvals and deduplicated reminders. Investigate public sources only when beginning this task. |
| P6: 2G operational acceptance | Existing tests are disposable; production readiness is not established | Least-privilege roles, webhook auth, pinned dependencies/images, supervision, redacted logs, health and backlog visibility, restore rehearsal, migration/rollback and recovery runbooks all validated in isolated synthetic environment. Review diff/evidence and obtain explicit owner approval before production access, cutover or deployment. |

P0 completed and P1 committed/pushed at `120b28a` (17 focused reminder tests
passed at that checkpoint). P2 now includes the owner-approved D10 policy and
additive migration 0003: legacy update/remove cannot target managed series,
including pre-conversion pending requests. Genuine legacy and v2 paths, stale
snapshots and concurrent conversion decisions passed the new focused SQL cases.
P3 exact-window/expiry/history/replan cases also passed; bounded metadata-only
quarantine inspection has offline tests. New work remains uncommitted because
Git metadata is read-only. See [evidence](M2_COMPATIBILITY_RECOVERY_RESULTS.md).
Remaining P2 adversarial cases, P3 receipts/audited resolution and later rows
are not declared complete. No additional architectural approval is required for
this patch; enabling resolution/resend and the Panchang provider policy remain
later decisions, not implicit permissions to mutate or send now.

2B, 2D, 2E, 2F and operational acceptance must each have reviewed evidence and
closed remaining gaps before Milestone 2 is complete. Passing one reminder is not
the milestone exit criterion. Keep 2C's passed synthetic scope; do not rerun it
without a relevant functional change. Checksum-corruption rejection remains a
selective migration acceptance gap; do not repeat unrelated integrations for it.

Each implementation task gets a focused branch/PR with source tests and sanitized
evidence; do not merge into main autonomously. Architecture/provider and sensitive
source decisions are owner gates. Routine fixes and focused verification proceed
within approved scope. These acceptance criteria are a plan, not passed results.
