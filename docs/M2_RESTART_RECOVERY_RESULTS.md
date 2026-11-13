# Milestone 2E restart/outage acceptance

Branch `development/m2-recovery-acceptance`, committed base `3d46d8e`.
The working tree was clean at entry. No application defect was demonstrated;
this checkpoint adds only focused synthetic acceptance and documentation.

## New verification

One new `restart-recovery` case passed on the pinned local PostgreSQL 17 image
and daemon `44c1ef83-c50e-4ecc-8f19-4b112bc40f29`. Five migrations and preserved
legacy contracts were verified before the case. It used the existing isolated
runner and exact authorized schema-only baseline, unchanged.

Each worker query runs in a fresh psql process authenticated as the restricted
worker login. Fixtures use a fixed simulated India-local noon tomorrow to avoid
midnight-dependent occurrence identities. No real wait for a six-hour outage or
HTTP transport is needed. The sequence:

1. Commit sent-with-receipt, explicit uncertain, unacknowledged leased and
   definitively rejected deliveries. Verify fresh sessions do not skip backoff.
2. Materialize an exact-lookback-edge occurrence and a cancelled future occurrence;
   exclude the occurrence one second outside lookback. Snapshot the full ledger.
3. Start a restricted-worker claim inside an uncommitted transaction; observe its
   PostgreSQL sleep after the claim. Stop only the disposable postmaster with
   immediate shutdown. The client fails; another connection confirms unavailability.
4. Start that postmaster again and verify a changed postmaster start time and an
   identical full committed ledger. The uncommitted claim did not survive crash
   recovery. SCRAM logins, wrong-password rejection, ACLs, logging settings and
   disabled reconciliation gate survive.
5. Claim and acknowledge the exact-edge occurrence once. Safe rejection retries
   only at the 30-second backoff edge. A prior-attempt token cannot acknowledge the
   new attempt. Sent, uncertain and active-lease rows cannot be reclaimed.
6. At exact lease expiry the pre-outage orphan is quarantined, token/lease cleared,
   attempts preserved and old acknowledgement rejected. Sent-with-receipt and
   explicit uncertain history remain byte-equivalent as JSON records.
7. Re-enable the cancelled occurrence at a new time on the same India date. The
   old due time cannot claim it; the new time uses the same delivery identity and
   can be acknowledged only once. Advancing one day yields no automatic replay.

PASS: postmaster outage/crash rollback, committed durability, worker reconnects,
lookback/backoff boundaries, expiry/stale tokens, uncertainty quarantine,
cancellation/replanning identity and duplicate suppression.

Only this new Docker case was run, once successfully. Existing recovery SQL,
receipt/concurrency/reconciliation, n8n and live Telegram acceptance were retained,
not repeated. Three materially affected runner preflight tests passed, including
new rejection of combined restart/reconciliation cases before Docker access.

## Isolation, authentication and privileges

A test-only shell supervisor keeps the disposable container running when its
postmaster stops. This preserves the existing tmpfs during process crash recovery;
**the container is never restarted**. Container restart/host failure loses tmpfs
and is not durable-volume/restore acceptance. No production Compose or persistent
volume is used. The supervisor is selected only for this individual case.

The runner verified read-only root, network none, no published ports or host
mounts and only tmpfs storage. HBA inspection before/after restart proved host
rules require SCRAM and trust rules apply only to local Unix sockets. Those
sockets are inside container-only tmpfs. Worker clients always use TCP localhost
with actual login credentials; an incorrect password is rejected. Host/daemon
administrators remain trusted and can inspect container environments.

Random credentials remain session-only: password provisioning uses stdin and
client authentication inherits PGPASSWORD by name, without password values in
arguments, printed diagnostics or repository files. Statement, duration,
sampling and parameter logging remain constrained before/after restart; the
restarted postmaster logs to /dev/null. No raw database errors/logs are published.
The worker cannot write the ledger directly, enable reconciliation, invoke
operator inspection or delete audit. Existing executor roles, migration bytes,
immutable audit triggers and the default-off gate are unchanged. Audit stays empty;
no reconciliation resolution/resend/reset is performed in this case.

Cleanup removed the disposable container and verified original running container
IDs unchanged. No Telegram/n8n operation, production credential/service access,
deployment or merge occurred. Source-safety, changed Python AST and explicit
safe-file whitespace/diff checks passed; Git metadata remains read-only.

## Retained evidence and remaining 2E limits

[Earlier recovery evidence](M2_COMPATIBILITY_RECOVERY_RESULTS.md) covers exact
six-hour boundaries, stale acknowledgement, immutable history and cancellation.
[Receipt evidence](M2_RECEIPTS_ADVERSARIAL_RESULTS.md) covers atomic receipts,
wrong/expired tokens, duplicate rollback and competing acknowledgements, plus
worker commit-failure/no-transport-replay behavior. [Reconciliation evidence](M2_RECONCILIATION_RESULTS.md)
covers operator concurrency/replay, immutable audit privileges and audit/state
rollback. Five-attempt cap/concurrent claims and the owner-approved single
Telegram reminder are earlier retained acceptance. None was rerun here.

The controlled-clock worker-session/postmaster recovery matrix is now satisfied
for these cases. It does not certify gateway supervisor restart, wall-clock
jumps, host reboot/disk loss, durable-volume restoration, every network partition
or external exactly-once delivery. Reviewed source/workflow adoption and 2G
restore/supervision/operational rehearsal remain. Real operator evidence authority,
identity/TLS and production reconciliation require separate review and approval;
production reconciliation remains disabled. Missing receipt/commit acknowledgement
never establishes non-delivery or authorizes a resend.

## Remaining 2D acceptance review

This is a review of existing source/evidence, not another test run or full 2D
completion claim.

| Exit criterion | Verified evidence / remaining work |
| --- | --- |
| Approval, requester authorization, stale snapshots, rejection/replay and bounded conflicts | Satisfied in the covered SQL/API cases: gregorian.sql, gregorian_adversarial.sql and adversarial-concurrency. Force does not bypass authorization or staleness; conflict overrides remain explicit. |
| Legacy/managed coexistence and transition races | Satisfied under D10: genuinely legacy behavior preserved; pending/new legacy managed mutations reject; fresh v2 remains usable. See compatibility results and legacy-concurrency. |
| Stable occurrence identity and occurrence/series separation | Covered occurrence update/removal, unaffected other dates, series removal, in-flight veto and sent/quarantined history preservation. Approved series recurrence changes combined with pre-existing overrides and future reminder materialization still need targeted exit evidence. |
| Gregorian calendar semantics | Covered monthly invalid-day skipping, leap-date matching, ISO-week interval anchors, daily interval and inclusive until. Full public proposal/approval/occurrence fixtures for weekly/yearly intervals, December/January transitions and multi-selector monthly/yearly combinations remain pending; predicate-only fixtures do not establish the full API matrix. |
| Conflict guarantees | Covered overlap, adjacency, rollback and concurrent decisions. The reviewed default horizon is 730 days, maximum 3660; infinite-series conflict freedom is explicitly outside the existing guarantee, not an unpassed test. Overnight events remain unsupported. |
| Trusted application/workflow integration | Synthetic DB API/requester checks are covered. Reviewed source adoption and actual managed-v2 owner approval/workflow wiring remain pending; direct SQL requester IDs are not a replacement for trusted application authentication. No production/workflow execution is authorized here. |

All Milestone 2, including Hindu Panchang source/tradition/reference decisions and
operational acceptance, must finish before other orchestrators. No new architecture
choice was needed for this test-only checkpoint.
