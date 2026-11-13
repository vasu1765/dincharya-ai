# Application migrations

0001_gregorian_occurrences.sql, 0002_occurrence_reminders.sql and
0003_managed_legacy_boundary.sql extend the reviewed
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
