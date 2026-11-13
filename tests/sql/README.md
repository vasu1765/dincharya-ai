# SQL test scope

Use only an explicitly authorized schema in fresh disposable PostgreSQL; never
production. gregorian.sql and reminders.sql cover the initial recurrence and
reminder foundations. New focused cases:

- legacy_coexistence.sql: genuine legacy decisions beside v2 series, authorization,
  replay/staleness and in-flight protection.
- legacy_managed_boundary.sql: owner-approved D10, pre-conversion requests, current
  ownership, direct/dispatcher force attempts, fresh submissions and continued v2.
- reminder_recovery.sql: exact lookback/expiry boundaries, stale ack, immutable
  history/quarantine and cancelled-work replanning.
- legacy-concurrency in the focused runner: conversion serialized with two legacy
  decisions and a new legacy submission; uses committed synthetic rows, destroyed
  with the disposable DB.

Select only needed cases with tests/integration/focused_application_runner.py:

```bash
python3 -B tests/integration/focused_application_runner.py --baseline EXACT_AUTHORIZED_SCHEMA --expected-daemon-id OPERATOR_PIN --case legacy_managed_boundary.sql --execute-approved
```

This runs PostgreSQL only, applies all three migrations, has no network/ports/host
mounts, prints no raw schema/errors/credentials and verifies cleanup. The three
SQL scripts roll back their fixtures.
Run legacy-concurrency last when selecting multiple cases; duplicate selections
are rejected before Docker starts. The original integration runner includes
these scripts for a future justified full application run; it was not rerun here.
See docs/M2_COMPATIBILITY_RECOVERY_RESULTS.md for observed evidence and limits.
