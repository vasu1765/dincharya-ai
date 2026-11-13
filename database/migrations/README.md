# Application migrations

0001_gregorian_occurrences.sql and 0002_occurrence_reminders.sql extend the reviewed
PostgreSQL schema. The baseline remains outside Git; its original provenance
manifest path has not been confirmed. Historical m2a SQL must not be replayed.

../migrate.py renders explicitly ordered migrations into a psql transaction with
a target guard, advisory lock and immutable SHA-256 ledger. It performs no I/O to
services itself and deliberately supports only dincharya_app_test. The isolated
application runner installed the authorized baseline unchanged and applied/replayed
the migrations successfully. The subsequently added corrupt-checksum runtime test
and multi-session checks remain unverified; see ../../docs/HANDOFF.md.

Never apply the baseline to existing production. Production adoption, privileges,
recovery/rollback procedures and migration execution require separate review and
authorization. Keep n8n metadata migrations separate from application migrations.
No production role, ledger, schema or workflow was changed.
