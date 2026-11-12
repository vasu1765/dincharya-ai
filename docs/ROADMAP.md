# Dincharya AI roadmap

Finish all of Milestone 2 before Milestone 3 or another orchestrator. Status and
recipes are not authorization. Read [HANDOFF](HANDOFF.md), [decisions](DECISIONS.md)
and [policy](DEVELOPMENT_POLICY.md) before proceeding.

## Current checkpoint

147 offline tests pass. Milestone 2A is complete and recorded in Git HEAD
62e96e6 (feat: complete Milestone 2A offline source tooling). The earlier sandbox
commit failure is historical; do not treat it as the current Git state. Later
2B/C source and documentation changes remain in the working tree, including
untracked files. Nothing is staged by the handoff task. Do not reset or clean them.

| Phase | Status | Remaining exit criteria |
| --- | --- | --- |
| 2A — offline hardening | Complete | Private-only preparation, strict source/provenance checks, synthetic tests; original checkpoint was 52 tests. Current suite includes subsequent regressions. |
| 2B — reviewed source synchronization | Private investigation complete; source adoption incomplete | Approved schema/snapshot/extraction/source evidence reviewed privately. 94 history versions; current/published preserved separately. 2/4 current structural candidates. Native scheduler state identified as class B, unchanged. Approve faithful native-state/Code representation and adopt reviewed source only after relevant validation; do not claim the live baseline is already in Git. |
| 2C — isolated integration | Configuration prepared; not executed | Approve first synthetic-only startup/DB initialization/import/execution/activation/restart/teardown scope. Verify health, isolation, fixture behavior and native import/persistence contracts. No production inputs or Code nodes. |
| 2D — advanced Gregorian recurrence | Not started | Reviewed source and integration evidence first; implement add/edit/remove, occurrence/series scopes, conflicts, proposals and approvals. |
| 2E — occurrence reminders | Not started | Stable occurrence identity, deduplication, retries, concurrency and outage-recovery tests. |
| 2F — Delhi Hindu recurrence | Not started | Agree source/calculation/tradition/location and reference dates; Panchang, Ekadashi and festivals with tested recurrence semantics. |
| 2G — integration/deployment preparation | Not started | Full regression and restore rehearsal, reviewed migrations/workflow diffs, recovery plan. Production execution/deployment needs separate approval. |

## Next implementation sequence

1. Read the handoff and inspect Git; rerun the offline suite. Do not reopen private
   data automatically. No Docker/import approval is currently in force for 2C.
2. Obtain an explicit scope for only the disposable 2C project and supplied
   synthetic non-Code fixtures. Verify local image IDs and host resource/UID needs;
   generate session-only test secrets without printing them or reading production .env.
3. After approval, use only tests/integration/compose.json with project
   dincharya-m2c-synthetic, --env-file /dev/null and --profile integration. Establish
   startup/health/isolation before any test DB query or synthetic import.
4. Configure a fresh synthetic owner/project if required. Import inactive manual
   smoke only within approved scope; execute and assert its synthetic Set result.
5. Inspect synthetic scheduler-state import preservation before activation. Then,
   if approved, exercise activation/recurrence/re-arming and restart n8n-test only
   while PostgreSQL stays up. Capture private results, including unexpected state
   changes. Do not infer persistence from manual triggering or reset real state.
6. Perform approved test teardown; PostgreSQL/tmpfs teardown loses synthetic data.
   Clear session secrets. Record integration evidence and limitations.
7. Use the evidence to resolve remaining private conversion contracts. Review source
   adoption separately before advanced feature work. Production imports/migrations,
   real Code execution, source promotion and deployment remain distinct gates.

## Evidence and validation limits

Private manifest types private_extracted_workflow_analysis_v2 and
native_scheduler_state_review_v1 were checked for this checkpoint. Published nodes
and connections were located; only one node position differs. Historical settings,
state, executing-version proof and import/persistence behavior remain unverified.
Detailed source hashes, identities and raw records stay private, not in this file.
Do not assume temporary report paths survive or that documentation grants access.

Offline checks: unittest discovery; Python and embedded-Python AST parsing; bash -n;
Node syntax checking for the mock only; integration JSON/contracts; explicit
safe-source scans; Git whitespace/index checks. These do not execute Docker,
SQL, native Schedule helpers or workflow Code. See [2C runbook](../tests/integration/README.md).

After Milestone 2: Adhyayan (spiritual/career learning), Arogya (fitness/vegetarian
nutrition), Atma-Chintan (accountability/reflection), Vittiya (recurring invoices
and approvals), then India-based VPS deployment and operational hardening.
