# Dincharya AI roadmap

Finish Milestone 2 before Milestone 3 or another orchestrator. Status is not
production authorization. See [handoff](HANDOFF.md), [policy](DEVELOPMENT_POLICY.md)
and [decisions](DECISIONS.md).

## Reminder gateway development branch

The opt-in PostgreSQL and Telegram adapters, explicit owner approval commands
and due-work polling are implemented for the first one-time reminder path.
Remaining acceptance includes executing the new approval/retry-cap SQL
assertions, checking concurrency, and verifying a single delivery with a
disposable database and dedicated Telegram test bot. Recurring series and
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
| 2D — advanced Gregorian recurrence | Initial migration and isolated SQL assertions passed | Add/update/remove, occurrence/series scopes, calendar boundaries, conflicts, stale proposals and approval foundations implemented. Expanded multi-session checks remain unverified; legacy API interaction, broader adversarial cases and application/workflow adapters need review. |
| 2E — occurrence reminders | Initial migration/SQL assertions and offline worker tests passed | Identity, deduplication, claims/leases, retry/backoff, uncertainty quarantine and bounded recovery foundations implemented. Concurrent claim check newly added but not integration-tested. Retry exhaustion, wider recovery tests, real adapter wiring and uncertain-send reconciliation remain. |
| 2F — Delhi Hindu recurrence | Not started | Agree calculation/source/tradition/location and reference dates; no new feature work in current stop scope. |
| 2G — deployment preparation | Not started | Restore/recovery rehearsal, full acceptance, reviewed migrations/workflow diffs and explicit production approval. |

## Preserved next-session work

1. Read the handoff; inspect status and preserve changes. Do not repeat the full
   integration suite without a functional change or unresolved runtime concern.
2. Obtain the exact provenance manifest path from the operator; do not guess or
   scan private directories. The authorized schema remains outside Git.
3. Review the new application-runner checksum-mismatch and concurrent decision/
   reminder checks. They were added after the last passing SQL run and were not
   executed; record this gap before selectively verifying them in the approved
   disposable stack in a resumed session.
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
