# Cycle 4 application integration and operational acceptance

## Verified on the repository fixture

| Check | Evidence |
| --- | --- |
| Application stack | PostgreSQL 17.12, real n8n 2.47.3 and real Telegram SDK with simulated Telegram I/O. The repository Webhook and HTTP Request nodes ran in a fresh n8n state directory. Only the disposable target and HTTP response handling were configured for the fixture. |
| Approval route | Confirmed private owner rule and occurrence approvals through the relay, denied foreign callbacks, invalid signatures, stale signatures and a worker key used for an owner request. Calculator owner-API grants were absent. |
| Annual and restart behavior | Annual orders and cancellations went through n8n. A new application process rejected the old button and recovered the stored rule. Two years projected separate appointments. A repeat calculation, repeated approval and alternate logical identity in the same year created no additional appointment. Cancellation retained the approved history. |
| Migration and relay recovery | The migration ledger matched the exact bytes of 0001 through 0010. Reapplication was a no-op. An intentionally changed digest was refused. The relay reported the application outage and resumed after restart. An n8n restart retained the published fixture and its webhook. |
| Reminder recovery | Overlapping materializer runs created one row per approved event and date tested. A definitive simulated rejection retried after the configured backoff and produced one accepted receipt. A simulated lost response and an expired send lease remained uncertain; neither was resent. A due reminder within lookback was recovered after restart, and one outside lookback was withheld. |
| Restore rehearsal | A logical dump of only the disposable application database was restored into a separate database in the same isolated cluster. The original database was retained as a comparison until teardown. Annual metadata, approval audit, delivery states and receipt presence survived, and a worker tick after restore sent nothing. |

The native relay initially returned 404 immediately after its activation API
completed. Waiting for a successful signed, read-only request before starting
the approval matrix resolved the startup race. An HTTP health check alone
cannot establish that n8n has registered the webhook.

The restore rehearsal reused the cluster's synthetic roles and OIDs. A
cross-cluster disaster restore must recreate scoped identities and explicitly
review OID-bound principals before reconnecting. A backup older than a send can
omit delivery history. A worker should remain paused until that gap is
reconciled. The rehearsal provides no basis for automatic resend.

Run the repository fixture in a workspace with Python dependencies from the
[Cycle 2 harness](M2H_CYCLE2_TELEGRAM.md), the pinned public kernel and
n8n 2.47.3 available locally.

```bash
OPENBLAS_NUM_THREADS=1 python -B tests/integration/m2h_operational_acceptance.py \
  --pg-bin /absolute/path/to/postgresql/17/bin \
  --n8n /absolute/path/to/n8n \
  --ephemeris "$DINCHARYA_PUBLIC_DE440S" --year 2027
```

Use `--pg-share` for a relocated PostgreSQL installation. The standalone
test binds to loopback with per-run state, fresh SCRAM credentials and an
in-memory simulated Telegram transport. It does not run the historical
workflow or a real bot. The fixture supplies no application-baseline credit.

## Exact application baseline

The approved schema-only snapshot exists outside Git in the original WSL
environment. It was absent from Work at the exact documented path. Earlier
baseline runs passed with the original scope and the pinned standalone
Docker project. Cycle 4 has a dedicated runner that reuses that project,
daemon and image checks, private database roles and repository-owned native
relay. The runner reads only the previously named schema file and verifies
its bytes remain unchanged. It performs no dump or restore of that input or
its test database. The exact-baseline Cycle 4 run now passes in WSL; see the troubleshooting checkpoint below.

One local handoff, for the Cycle 4 draft branch in the original WSL checkout
with the existing pinned dependencies and public kernel configured:

```bash
OPENBLAS_NUM_THREADS=1 python -B tests/integration/m2h_baseline_acceptance.py \
  --expected-daemon-id 44c1ef83-c50e-4ecc-8f19-4b112bc40f29 \
  --ephemeris "$DINCHARYA_PUBLIC_DE440S" --year 2027 --execute-approved
```

Return the pass/fail headings and exit status through issue #6. Keep the schema,
container logs, role settings and credentials local. The command uses the
exact previously reviewed WSL path; a different path or source needs owner
authorization. The local baseline runner was checked for fail-closed preflight
and shares the tested SDK/annual cases. Its Docker runtime remains unverified in
Work.

## Supervision and advance reminders

Development preflight exposes no reminder tick. The older fixture gateway
has one in-process job owner, and the worker uses the database lock and leases.
Production still needs a supervised single poll owner, a signed relay readiness
probe, a last-successful-tick and backlog check, and alerts for uncertain work.
Supervision should restart the process without resetting leases or delivery
history. A replay decision after a possible send requires separate evidence.

The current identity is event plus local occurrence date, so it represents one
reminder at the appointment start. Advance reminders need stable slot identity
per approved occurrence, explicit offset and timezone semantics in the preview,
independent slot-level deduplication, and tests for old deliveries,
cancellation, outage and restore. Adding an advance slot under the existing
identity would overwrite or suppress the appointment reminder. This cycle
leaves that work gated.

## Release readiness

**Keep real lunar scheduling disabled.** Preserve Drik Delhi as primary,
IMD PAC as secondary, the 90-second publisher diagnostic and the 300-second
sunrise guard. The remaining gates are:

- Exact-baseline acceptance with native n8n and simulated Telegram passed. Review
  this scoped role/trigger compatibility evidence before any promotion.
- Resolve 2B original provenance. The repository documents the schema capture
  and the current/published workflow distinction, and identifies no exact
  original manifest location. The owner can supply the exact manifest path
  and authorize reading that file alone, or choose a new reviewed source-adoption
  route. Referenced inputs would require their own scope. The invented schema
  and repository-owned relay are separate evidence.
- Broaden calendar adoption evidence, implement and review advance slots,
  validate supervised recovery and cross-cluster restore, then obtain explicit
  owner approval for any real Telegram lunar acceptance. Preserve earlier
  private delivery acceptance within its original scope.

## WSL troubleshooting checkpoint

The first exact-baseline attempt exited 1 after isolated service startup and
verified teardown. Fixed-label diagnostics localized the failure to application
service startup: the Cycle 4 launcher passed a `Path` to the Unix socket server.
The working M2G launcher passes a string. An offline reproduction raised
`TypeError`; the correction converts only this socket argument to a string.
The schema input, migrations, authorization and calendar assertions are unchanged.

The runner now reports fixed checkpoints for safety preflight, schema loading,
migrations, transport fixtures, scoped identities, socket relays, checksum
verification, application startup, native n8n, SDK approvals, annual recovery and
input integrity. Teardown retains its separate removal and inventory checks.
Failures print the last fixed stage; exception text, SQL, private paths, child
stderr and container output remain suppressed. Setup errors can still be
followed by cleanup errors; retain both stage and teardown evidence.

Two offline regressions cover the string socket address/readiness/shutdown
protocol and suppression of exception details in failure diagnostics. The 39
existing integration-runner tests pass. Source scanning passes for the other
three changed Python files. The shared runner is rejected by the source scanner
in both HEAD and the modified version; its two added fixed diagnostic lines
were manually reviewed. No scanner rule was relaxed.

### Actual focused rerun result

**PASS — exit 0.** After the socket correction, the documented exact-schema
runner passed schema initialization, migrations 0001–0010, ledger checksums and
repeat installation, scoped calculator restrictions, native signed n8n relay,
actual SDK owner approvals and foreign-callback/duplicate rejection. Annual
checks passed across application restart, separate yearly projections, stable
identity, stale cancellation and expiry rejection, duplicate suppression and
one reminder row. Original schema bytes were checked unchanged. Disposable
teardown and unchanged unrelated running-container IDs passed.

The diagnostic rerun first isolated the startup failure (exit 1) and cleaned up;
one materially affected rerun after correction passed (exit 0). No schema,
migration, authorization assertion or calendar model was altered. No actual
Telegram request, production access, deployment or merge was performed.

This baseline runner does **not** repeat the broader repository-fixture outage,
relay-restart, uncertain-delivery or restore matrix; its earlier evidence remains
separate. It provides no 2B provenance, advance-slot or production adoption credit.

Focused offline results: 2 new launcher tests and 39 existing runner regressions
passed; changed Python AST and diff checks passed. The broader supplementary
annual/application unit command was stopped (143) after a sandbox executor-shutdown
stall and is not claimed as passed. The real SDK approval path subsequently passed
inside the isolated acceptance run. No broad or unrelated suite was repeated.
