# M2F PostgreSQL integration — offline implementation checkpoint

## Status and exact scope

Base pushed `81acd6a8240f474b0bdabf4d73a79f1433b9a08c` (design), clean entry on
`development/m2f-memory-contract`. Owner created
`development/m2f-postgres-integration` and agent verified it. Git metadata is
mounted read-only: implementation is uncommitted until the owner executes HANDOFF
commands. No alternative Git/remote write path was used.

The latest instruction authorizes implementation, offline verification and harness
preparation. It expressly withholds PostgreSQL connections and Docker execution.
**No SQL has been installed, parsed by PostgreSQL, or exercised against a database.**
T00–T26 below are implemented acceptance assertions awaiting execution; they are
not passing runtime evidence. This checkpoint is not a working synthetic E2E claim.

## Implementation

[0006](../database/migrations/0006_synthetic_lunar_approval.sql) is a new numbered,
checksummed, transactional migration, restricted to `dincharya_app_test` installed
by `synthetic_test`. Migrations0001–0005 are unchanged. Native generator, conflict
predicate, claim/finish/receipt APIs and delivery worker code are unchanged.

Six tables replace the proposed seven: principals, profiles, series, occurrences,
calculations and actions. **Actions combine immutable approved revisions with the
append-only decision audit.** Every final decision records the frozen request,
before/after occurrence or series snapshot, reviewed calculation/delivery/conflict
state and linked native child request. Series cancellation records each affected
member's post-decision snapshot as well as the reviewed manifest. A partial unique
index permits at most one final decision per request; blocked conflict attempts
are immutable replayable outcomes while the request stays pending.

- Immutable UUID series scope typed v2 calendar-key uniqueness. One logical
  occurrence keeps one projection event ID; profile/date are not key fields.
- Native managed Gregorian `once` projection per approved occurrence. Proposal,
  inspection, approve/reject, replacement and cancellation use `lunar_api`.
  Existing schedule_change_requests are reused, with explicit lunar-1 envelopes.
- Approval calls existing Gregorian proposal/decision inside one transaction;
  failed child decisions cannot leave events/requests/approvals partially committed.
  The legacy event_date column is synchronized with the approved once-rule date.
- Shared `(20261112,1)` mutex, ordered row locks and current snapshot fingerprints
  prevent stale/ABA/conflict-set decisions. Exact decision UUID/command/principal
  replay returns the recorded result only after fresh login/owner authorization;
  changing a principal mapping cannot disclose a former owner’s replay. Historical
  producer/decider names and OIDs remain in immutable records. No automatic client
  retry or new action ID.
- Trusted session_user OID/name mapping derives owner_subject. Owner, calculator
  and existing reminder worker have separate scoped roles. No actor/user ID input.
  Principals start disabled; profile rows must be explicitly provisioned immutable
  synthetic descriptors, SHA-256 bound to PostgreSQL JSONB text. Descriptor must
  retain upstream engine/kernel/model/profile metadata when real research outputs
  are used; current runtime fixtures are invented, not astronomical evidence.
- Non-login/non-superuser executor; no caller membership. Fixed search_path and
  qualified objects, parameterized Python adapter, no DSN/secret/environment load.
  Executor ledger access is SELECT and UPDATE(status), not receipt/lease/attempt
  editing. Principals changes serialize with the scheduler mutex.
- Mapped-event/request/rule/override triggers protect both OLD/NEW references.
  Auth is execution-role based, never a caller GUC. A boolean-only public helper
  lets invoker guards read mapping existence without granting private-table reads.
  The helper exposes existence only, no owner/date/title/evidence.
- Earlier0003 legacy guard is preserved inside an additive wrapper, allowing only
  the trusted executor's lunar envelope. Dispatcher explicitly refuses lunar or
  unknown tagged requests through the caller-ID/legacy path. Native entry points
  cannot mutate mapped events. Existing ordinary grants are removed in this
  synthetic setup; no production ACL rollout is authorized.
- Reject installation if unreviewed public SECURITY DEFINER functions exist.
  Fresh synthetic catalog/ACL validation remains essential; unadopted baseline
  entry points are not certified by offline inspection.

[Python adapter](../prototypes/panchang/postgres_contract.py) is opt-in under
prototypes and not imported by gateway/n8n/worker. Injected authenticated connection
contexts commit each operation before returning. SQL/commit errors are sanitized
and never automatically retried; callers inspect/replay the original action ID.
There is no send, claim, finish, connection factory configuration or workflow wire.
Date/time payloads require ISO dates and literal clock times; relative values
(`now`, `tomorrow`) and locale-dependent dates reject. Evidence intervals require
explicit offsets. API DateStyle/TimeZone are pinned to ISO,YMD/UTC so caller settings cannot
reinterpret approved fields or change snapshot fingerprints. This is implemented
and awaiting the prepared runtime regression, not a compiled SQL claim.

## Policy and history

One at-event reminder per projected occurrence uses existing event/date uniqueness.
Advance/multiple reminder slots remain a full Milestone2 requirement; this limited
synthetic seam does not implement them. Birth interpretation and repetition policy
are part of approved series/occurrence snapshots; same-day policy changes need
new approval. Existing projected occurrences are never implicitly rewritten by a
series-rule decision. Changed key interpretation after any projection requires a
future reviewed identity mapping and is currently rejected, rather than creating
new events to evade history. No v1 adoption/backfill or restore operation.

Never-attempted replacement checks **all dates** of the projection's ledger:
no rows, or only pending/cancelled attempts0. Any sending row, including expired,
blocks changes until the existing worker quarantine stabilizes the outcome.
Attempted/failed/dead/sent/uncertain records block date/time/title replacement.
Same projection/provenance approval can append audit without updating the event,
queue or old approval records. Cancellation disables the projection, cancels
pending/definitively failed work preserving attempt counters and other fields,
and leaves sent/uncertain/dead rows unchanged. Tombstones cannot be restored.

Series cancellation approves an exact manifest of at most64 projections, disables
all members and the series atomically, and blocks new approvals. A changed manifest
or one sending member rejects the entire operation. Unsupported/skipped/ambiguous/
unselected/Kshaya data has no selectable date. The DB validates bounded typed
producer evidence and interval containment; **it cannot independently certify
astronomy**. Engine/date release gates remain unchanged, with no new model evidence.

## Verification and pending runtime matrix

Offline command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_lunar_postgres tests.test_migrations tests.test_focused_application_runner -v
```

19 tests passed:8 transaction/adapter tests,4 packaging/harness tests,4 existing
migration-renderer tests,3 affected runner preflight tests. Transaction tests use
mocks, including commit failure, rollback, sanitized errors, parameter injection,
exact action replay and no implicit retry. Preflight tests mock subprocesses and
prove missing execution approval, mixed/duplicate cases, symlinks and wrong daemon
stop before container creation. The initial packaging test had an incorrect API
count; its expected named API set was corrected. This was a test expectation error,
not PostgreSQL red-before-fix/runtime evidence.

AST, SQL lexical framing, explicit source-safety and diff checks are required for
this checkpoint. Lexical framing is not a PostgreSQL grammar/PLpgSQL compiler check.
No new dependencies or model files; no unrelated accepted suites rerun.

| Acceptance IDs | Implemented runtime assertions | Status |
| --- | --- | --- |
| T00–T02 | Catalog/role/daemon/SCRAM boundaries, bad password, cross-role/disabled identity, malformed/injection payload | Pending authorized DB execution |
| T03–T06 | Rule reject/approve, unapproved isolation, overlapping calculations/replay, distinct birthday/wedding conflicts, ordinary/Adhika sibling scope | Pending |
| T07–T09 | Parallel same/different decisions, ABA observations, changed birth/repetition snapshots | Pending |
| T10–T12 | Audit fault rollback, lost-response replay, stable-ID never-attempted replacement and event_date parity | Pending |
| T13–T16 | Terminal/attempted history gates, cancellation/refresh tombstones, manifest-vs-approval race, mapped raw/native boundaries | Pending |
| T17–T21 | Real API projection/refresh/due-claim/receipt path, concurrent claims, controlled two-order claim/edit lock waits, expired lease/stale ack, cap/backoff, receipt uniqueness/rollback | Pending |
| T22–T25 | Unmapped Gregorian overrides/cancel, unresolved inputs, profile change/key mapping refusal, immutable/least-privilege boundaries | Pending |
| T26 | Disposable postmaster crash/restart, action replay and exact terminal-history/uniqueness persistence | Pending |

The runner isolates lunar acceptance from all existing case selections. Only
`--case lunar` adds0006; ordinary2D/2E cases retain migrations0001–0005. Reuses the
pinned local PostgreSQL17 image/daemon checks, no-network/tmpfs/no-port container,
SCRAM TCP inside that container and local trust confined to its Unix socket.
The genuine API-to-ledger test waits at most45 seconds for a30-second future
server-clock due time; other history fixtures are explicitly administrator-seeded.
No fake future worker clock or real transport is used. Session-generated
credentials remain in memory/inherited environment and SQL stdin,
never values in argv, source or output. Server statement/error-parameter logging
is suppressed before credential provisioning. Existing service IDs and cleanup
are checked by the harness. **These inherited safeguards have not been re-executed
for the new case.**

## Exact remaining gated execution

After explicit owner authorization for this specific disposable acceptance run
(and narrowly scoped sandbox execution permission if needed), run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B tests/integration/focused_application_runner.py \
  --baseline /home/vasu1765/dincharya-backups/baseline-20261112T132918Z-d5V7Hf/application-schema.sql \
  --expected-daemon-id 44c1ef83-c50e-4ecc-8f19-4b112bc40f29 \
  --case lunar --execute-approved
```

This command is **not executed or authorized by this checkpoint**. It loads only
the named schema, validates daemon/isolation before test setup, executes T00–T26,
restarts only the disposable postmaster and verifies cleanup/service invariance.
Do not run successful live Telegram/n8n acceptance again. Fix demonstrated runtime
failures and rerun affected cases once authorized; do not claim a working workflow
until installation, assertions, concurrent sessions and cleanup actually pass.

Remaining: database grammar/catalog/permission/runtime compatibility, actual race
and rollback evidence, then review of validated preview ingestion and wider
reminder-slot policy. No production adoption, workflow integration or real send.
