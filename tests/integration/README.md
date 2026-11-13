# Synthetic integration runbook and results

The latest instruction is to stop development/testing and preserve progress.
Do not rerun Docker or the full regression suite merely to repeat passing results.
See ../../docs/HANDOFF.md for current authority and unverified additions.

## Isolation contract

Use only compose.json, project dincharya-m2c-synthetic, --env-file /dev/null and
--profile integration. Never merge production Compose. Verified local image IDs
are pinned; pulls/restarts are disabled. Three services use an internal network,
no published ports, no production mounts, no named volumes, bounded tmpfs storage,
read-only roots and individual read-only synthetic fixture mounts. No bot polling,
real credentials, production state or Code workflow is permitted.

runner.py creates an empty temporary Docker config and HOME, pins the local Unix
socket and verifies Linux Docker Desktop identity against a separately verified
daemon ID. It rejects remote context/host/TLS overrides and pre-existing test
resources. The user's Docker config/context and production .env are not read.
Project-specific cleanup runs after partial startup or failure; forced termination
or daemon failure can still leave resources. Host and Docker resources are shared.

## Last successful workflow run

2C passed with n8n 2.47.3 / nodes-base 2.47.2: health and runtime isolation;
synthetic DB initialization; owner/bootstrap; exact manual synthetic-pass;
activation; five successful fast scheduled outputs; PostgreSQL-preserving n8n-only
restart; three successful emissions started after readiness; durable job and
occurrence identity persistence; non-regressing clocks; retained legacy arrays;
unique observed cadence slots; deactivation/drain; verified teardown with original
running container IDs unchanged. This includes the final task error/retry checks.

The image's default durable scheduler intercepts Schedule Trigger rules and uses
scheduled_job/scheduled_task. Legacy arrays are preserved but were not proven to
drive that runtime. The synthetic seven-minute rule is a durable 420-second
interval; its full emission interval was not observed. No legacy mode was forced.

Native CLI import preserves staticData; the create API drops it. CLI operations
use internal broker port 5680 beside server port 5679. Test n8n requires a bounded
UID-1000 cache tmpfs while retaining a read-only root. api-client.js reuses synthetic
session cookies in private tmpfs to avoid login throttling.

## Last successful application run

application_runner.py loaded only the exact authorized schema into the fresh
dincharya_app_test DB, preserving source bytes and validating its schema-only
framing. Both application migrations applied; repeated application was a checked
no-op. gregorian.sql and reminders.sql passed, followed by verified teardown.
No original schema or private provenance was copied into Git.

Coverage includes calendar boundaries, occurrence overrides/cancellations, stale
and unauthorized decisions, conflict rollback/force, adjacent ranges, proposal
idempotence, reminder identities, duplicate claim rejection, token fencing,
backoff, sent-row preservation, legacy ledger preservation, ambiguous lease
expiry quarantine, bounded catch-up and cancellation.

Later additions to application_runner.py have **not** run in integration:
checksum-corruption rejection, parallel replay of a decision, competing reminder
claims and concurrent-test acknowledgement. The attempted expanded execution was
interrupted before a runtime result was returned. Do not invalidate or replace
the last successful run with an assumed result for these checks.

## Resumed execution only when justified and authorized

Workflow entry point: runner.py --execute-approved --expected-daemon-id ID.
Application entry point: application_runner.py --execute-approved
--expected-daemon-id ID --baseline EXACT_AUTHORIZED_SCHEMA_PATH. Never guess paths
or discover backups. These are recipes, not instructions to run during the stop
checkpoint. The original provenance manifest path remains missing.

The application migration renderer is transactional, checksummed and deliberately
restricted to dincharya_app_test. It is not a production migration/restore runner.
The original schema must never be replayed over an existing application database.

The unchanged safe-source heuristic flags generated/in-memory and invented test
password assignments. Matches were manually reviewed; no scanner was weakened.
External exactly-once delivery, real Telegram compatibility, all legacy functions
and historical runtime behavior are not established by these synthetic tests.

## Lunar synthetic end-to-end runner

synthetic_e2e_runner.py reuses this same standalone compose/project and pinned
images for a fixture-only native n8n webhook -> existing lunar adapter/worker ->
simulated transport journey. It does not rerun the old cadence or T00–T26 suite.
Compose explicitly configures host SCRAM and container-local socket trust. See
[actual E01–E05 evidence/command](../../docs/M2F_SYNTHETIC_E2E_RESULTS.md). The new
HTTP/stdio/psql bridge is test instrumentation, not a production route/driver.
No host port or new scheduler/worker, Code node or real Telegram call is added.
