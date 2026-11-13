# Dincharya AI roadmap

Finish Milestone 2 before Milestone 3 or another orchestrator. Status is not
production authorization. See [handoff](HANDOFF.md), [policy](DEVELOPMENT_POLICY.md)
and [decisions](DECISIONS.md).

## Milestone 2 completion roadmap

PR #1 merged into main at `f3db2ff600dbb417e8bd2c553aad5388697cbd9e`, including
owner-approved reminder evidence and HTTP 429 quarantine. Complete ALL Milestone 2,
including Hindu Panchang and operational acceptance, before other domains or
orchestrators. The prioritized [implementation plan](MILESTONE2_PLAN.md) reviews
2B/2D/2E against existing source/tests and defines acceptance and approval gates.

Restart/outage acceptance is pushed at `ff6198d`, following reconciliation
`3d46d8e`. The next local checkpoint completes the requested outstanding 2D
synthetic recurrence/API matrix: intervals/selectors, year/leap boundaries and
approved series edits over existing overrides/cancellations/future reminders.
No application defect required a migration. See [2D evidence and exit matrix](M2D_RECURRENCE_ACCEPTANCE.md).
Full managed-v2 integration remains blocked by reviewed 2B adoption; smallest next
step is owner-supplied original manifest path/read-only authorization, without
private-directory searches. Production reconciliation and resend/reset stay disabled.

Completed 2C/live-reminder acceptance is retained without repeating it. Full
Milestone 2 closure still requires reviewed source adoption, remaining recovery/
operational acceptance and Hindu Panchang before other domains/orchestrators.

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
| 2D — advanced Gregorian recurrence | Synthetic database/API matrix passed; integration blocked by 2B | Add/update/remove, occurrence/series scopes, calendar boundaries, conflicts, stale proposals and approval foundations implemented. Parallel duplicate decision check passed; D10 and the requested authorization/stale/invalid-argument/concurrency matrix passed; outstanding calendar/series API fixtures now passed; full trusted application/workflow integration remains blocked by 2B adoption. |
| 2E — occurrence reminders | Initial migration/SQL assertions and offline worker tests passed | Identity, deduplication, claims/leases, retry/backoff, uncertainty quarantine and bounded recovery foundations implemented. Concurrent claims, five-attempt cap and one-time gateway delivery passed. Exact lookback/expiry, immutable history and replanning passed; metadata-only inspection added. Nullable receipt persistence/atomic acknowledgement now passed; controlled-clock worker/postmaster restart matrix now passed; gateway supervision, host/disk/restore and production operator/operational review remain. Audited synthetic reconciliation passed. |
| 2F — Delhi Hindu recurrence | Not started | Agree calculation/source/tradition/location and reference dates; implement and validate Hindu scheduling before completing Milestone 2. |
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
