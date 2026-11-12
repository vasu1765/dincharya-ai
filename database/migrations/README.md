# Application migrations

The live application schema, once reviewed, becomes an immutable baseline for
empty development/test databases. The `m2a/` directory is historical and is not
the migration chain. n8n manages its own internal database migrations.

Future application changes use `NNNN_description.sql`, immutable SHA-256 checksums,
and a ledger recording version, checksum, application timestamp, and tool version.
A future runner must require an explicit target, acquire a migration lock, stop
on mismatches, and run each supported migration in a transaction with failure-on-
error behavior. Nontransactional operations require a separate reviewed procedure.
No runner or ledger is installed by Phase A.

Existing production must not replay the baseline. A later adoption operation
requires a normalized schema comparison, role/privilege reconciliation, backup,
and explicit approval before recording the baseline version. Restoring a backup
is a separate recovery operation, not a substitute for a migration rollback.

Verify future migrations in empty and previous-version isolated databases using
synthetic fixtures. Prefer compatible expand/contract changes. Pair workflow
changes with the application schema versions they require. Deployment, imports,
activation, production ledger creation, and migrations require separate approval.
