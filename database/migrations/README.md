# Application migrations

0001_gregorian_occurrences.sql, 0002_occurrence_reminders.sql and
0003_managed_legacy_boundary.sql and 0004_telegram_receipts.sql extend the reviewed
PostgreSQL schema. The baseline remains outside Git; its original provenance
manifest path has not been confirmed. Historical m2a SQL must not be replayed.

../migrate.py renders explicitly ordered migrations into a psql transaction with
a target guard, advisory lock and immutable SHA-256 ledger. It performs no I/O to
services itself and deliberately supports only dincharya_app_test. The isolated
application runner installed the authorized baseline unchanged and applied/replayed
the initial migrations successfully. Concurrent decisions/claims and the new
managed-boundary cases now passed; corrupt-checksum rejection remains a separate
unexecuted runtime check. See ../../docs/HANDOFF.md.

Never apply the baseline to existing production. Production adoption, privileges,
recovery/rollback procedures and migration execution require separate review and
authorization. Keep n8n metadata migrations separate from application migrations.
No production role, ledger, schema or workflow was changed.

0003 implements the owner-approved compatibility policy: legacy update/remove
submission and approval cannot target an m2d-managed series. Pending requests are
checked against current ownership under the same advisory lock as v2 decisions.
The original legacy proposal/decision bodies are retained verbatim in nested
guarded blocks, with definitions/ACLs/ownership/security properties preserved;
no bypass alias or privilege elevation is introduced. Unsupported definition
format fails closed for explicit review. Existing migration bytes are unchanged.

Select only new cases with tests/integration/focused_application_runner.py, using
an explicitly authorized schema path and daemon pin, `--execute-approved` and
one or more `--case` values: legacy_coexistence.sql, legacy_managed_boundary.sql,
reminder_recovery.sql, legacy-concurrency. This starts PostgreSQL only, on tmpfs,
with no network/ports/host mounts, verifies legacy function properties and removes
the disposable container. It does not invoke n8n, Telegram or production.

0004 adds nullable chat/message receipt fields, paired/state checks and unique
receipt identity. New acknowledge_occurrence_reminder delegates the existing
live-token/lease check and stores sent state plus receipt atomically. Its old
four-argument counterpart remains unchanged for old workers; unknown historical
IDs stay NULL. No backfill, operator resolution or resend function is added.
Apply all four migrations before starting the updated gateway; startup now fails
closed without the receipt migration/API. Synthetic upgrade tests preserve a
pre-existing sent row and the original acknowledgement body.

Additional focused cases: gregorian_adversarial.sql, telegram_receipts.sql,
adversarial-concurrency and receipt-concurrency. Run one committing concurrency
case last; use separate invocations for multiple concurrency cases. New cases
verify authorization/staleness/conflicts and receipt upgrade/failure/race safety.

0005_synthetic_reconciliation.sql is optional **synthetic-only** infrastructure,
not a production enablement migration. It refuses any database/admin other than
dincharya_app_test/synthetic_test and refuses existing fixed roles: use a fresh
disposable cluster. It adds NOLOGIN executors, separate operator/worker group
roles, private immutable destination/evidence/authorization records, append-only
audit and a default-disabled synthetic gate. Callers have only scoped API access;
fixture-admin provisioning is not a production trust workflow. No original
migration/function body or historical delivery is rewritten. Gateway preflight
still requires only 0001–0004; do not install 0005 on existing services.

The focused runner applies all five in a disposable PostgreSQL cluster. Select
`reconciliation-concurrency` for full synthetic action/privilege/rollback/race
coverage, or `reconciliation-review` only for post-row-lock permit expiry,
effective credential-safe logging settings and SCRAM negative authentication.
Reconciliation cases run individually. Successful existing acceptance should not
be repeated without a relevant change. No Telegram API call occurs. See
../../docs/M2_RECONCILIATION_RESULTS.md for observed results and limitations.

## 0006 — isolated lunar approval integration (not yet executed)

0006_synthetic_lunar_approval.sql adds six private identity/provenance/authority/
audit tables and scoped lunar_api functions over existing Gregorian once events.
Approved revisions share immutable action audit snapshots; existing requests and
reminder ledger are reused. Installation requires synthetic_test/dincharya_app_test;
profiles and trusted principals need deliberate synthetic fixture provisioning.
No worker/receipt/generator bodies or older migration bytes change. Mapped-event
mutation guards, limited legacy/dispatcher wrappers and synthetic-only ACL lockdown
are additive; not a production privilege rollout or astronomical engine adoption.

Only `--case lunar` in the focused runner appends0006; previous selections keep
0001–0005. The19 offline checks pass; T00–T26 runtime assertions await separate
execution authorization. See [results](../../docs/M2F_POSTGRESQL_RESULTS.md) for
exact gated command and limitations. Do not run this against an existing service.

## 0007/0008 — demonstrated lunar runtime corrections

0007 qualifies the record_calculation local command binding (42702).0008 fixes
search_path on the baseline sync_legacy_recurrence_rule invoker helper (42P01),
without changing its body/ACL/owner/security mode; temp lookup is explicitly last.
Earlier0001–0006 files remain byte-identical. Only the lunar runner case loads
0006–0008. Owner-authorized T00–T26 now pass, plus20 offline tests, with cleanup
and unchanged unrelated service IDs confirmed. See the results report. No
production migration/application or scheduling-engine adoption is authorized.

## 0009 — owner-scoped application inspection

0009_lunar_delivery_status.sql adds delivery_status(uuid) and owner_identity()
under lunar_api. Trusted session_user principal lookup, owner-only grants and a
latest20-record metadata bound expose state/attempt/due/receipt presence without
chat/message IDs, payload or worker tokens. No event/ledger schema mutation or
new role/table. Earlier0001–0008 bytes unchanged. M2G application acceptance
installed0001–0009 and passed G01–G04; ordinary worker’s owner-API call rejects.
Production migration/application remains unapproved; see M2G_TELEGRAM_RESULTS.md.
