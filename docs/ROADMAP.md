# Dincharya AI roadmap

Finish Milestone 2 before Milestone 3 or another orchestrator. Status is not
production authorization. See [handoff](HANDOFF.md), [policy](DEVELOPMENT_POLICY.md)
and [decisions](DECISIONS.md).

## Reminder gateway development branch

Final review at `43ad653`: no merge conflict; PR is draft. A reproduced HTTP 429
early-retry defect is fixed locally by quarantining flood-control responses for
manual recovery; automatic retry_after support remains follow-up work. Fifteen
focused reminder tests pass. Owner commit/push is needed because Git metadata is
read-only; see HANDOFF.md and PR1_PREMERGE_REVIEW.md. No live test repeated.

2026-11-13: WSL Codex resumed as primary developer at PR head `aa05dd2`.
With owner-authorized scoped execution, daemon/image/isolation, focused reminder
SQL (approval and retry cap), concurrent decisions/claims/acknowledgement and
PostgreSQL advisory-lock checks passed. Disposable cleanup passed with original
running container IDs unchanged. One explicitly owner-approved Telegram reminder
passed pending-proposal, owner approval, scheduling, held-lock suppression, single
delivery/acknowledgement, no-repeat observation and cleanup. Owner confirmed
exactly one reminder; no production service was used.
Git metadata remains read-only. See HANDOFF.md and PR1_FOCUSED_ACCEPTANCE_RESULTS.md.

The opt-in PostgreSQL and Telegram adapters, explicit owner approval commands
and due-work polling are implemented for the first one-time reminder path.
Focused approval/retry-cap SQL, concurrency and one live dedicated-bot reminder
now pass. PR #1 is ready for final evidence review and remains draft/unmerged.
Recurring series and
occurrence edits remain available through the PostgreSQL proposal API.

## Historical checkpoint

196 offline tests passed at the last full regression checkpoint. Final focused
checks passed: four migration-renderer tests, six worker tests and relevant Python
AST checks. The user requested stopping further development/testing to preserve
usage. Work is uncommitted and unstaged; preserve all working-tree changes.

| Phase | Status | Remaining exit criteria |
| --- | --- | --- |
| 2A — offline hardening | Complete | Original tooling recorded at HEAD 62e96e6; subsequent regressions included. |
| 2B — source synchronization | Investigation complete; adoption incomplete | Exact schema inspected under operator authorization. Original provenance manifest path is missing from the named docs; no private search permitted. Workflow/Code acceptance and reviewed source adoption remain gated. |
| 2C — isolated integration | Passed for synthetic default runtime | Health/isolation, manual output, activation/successful scheduling, n8n-only restart, durable job/occurrence persistence, observed duplicate checks and teardown passed. Historical/legacy engine behavior and real workflow import are not certified. |
| 2D — advanced Gregorian recurrence | Initial migration and isolated SQL assertions passed | Add/update/remove, occurrence/series scopes, calendar boundaries, conflicts, stale proposals and approval foundations implemented. Parallel duplicate decision check passed; legacy API interaction, broader adversarial cases and application/workflow adapters need review. |
| 2E — occurrence reminders | Initial migration/SQL assertions and offline worker tests passed | Identity, deduplication, claims/leases, retry/backoff, uncertainty quarantine and bounded recovery foundations implemented. Concurrent claims, five-attempt cap and one-time gateway delivery passed. Wider recovery tests and uncertain-send reconciliation remain. |
| 2F — Delhi Hindu recurrence | Not started | Agree calculation/source/tradition/location and reference dates; no new feature work in current stop scope. |
| 2G — deployment preparation | Not started | Restore/recovery rehearsal, full acceptance, reviewed migrations/workflow diffs and explicit production approval. |

## Preserved next-session work

1. Read the handoff; inspect status and preserve changes. Do not repeat the full
   integration suite without a functional change or unresolved runtime concern.
2. Obtain the exact provenance manifest path from the operator; do not guess or
   scan private directories. The authorized schema remains outside Git.
3. The concurrent decision/reminder checks now pass. Checksum-mismatch rejection
   remains unexecuted; verify it selectively when continuing migration acceptance.
   Do not repeat the completed live reminder without new owner authorization.
4. Continue 2D/2E acceptance and adapters before declaring those milestones complete.
   Infinite-series conflict freedom and external exactly-once Telegram delivery
   are not claimed. The default conflict horizon is 730 days; reminder catch-up
   defaults to six hours and uncertain sends are never blindly retried.
5. Stage/commit only when authorized, using explicit safe paths in HANDOFF.md.
   Production SQL, bot use, real Code, source promotion and deployment remain
   separately gated. Do not replay the baseline against an existing database.

## Important integration findings

The tested n8n 2.47.3 / nodes-base 2.47.2 image defaults to durable scheduling.
It stores active jobs/occurrences in scheduled_job/scheduled_task; legacy native
arrays remain preserved but were not proven to drive this execution path. Create
API drops staticData; native CLI import preserves it. Successful test teardown
removed disposable resources and confirmed original running container IDs unchanged.
No production resources/data, credentials, bot, Code nodes or scheduler state were
used. The latest expanded application-test execution request was interrupted; it
must not replace the recorded successful integration result.

After Milestone 2: Adhyayan, Arogya, Atma-Chintan, Vittiya, then operational
hardening and separately approved India-based VPS deployment.
