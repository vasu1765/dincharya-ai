# Dincharya AI — Milestone 2A

This creates a separate PostgreSQL application database and seeds a proposed routine. Review the events before enabling reminders.

## 1. From Ubuntu WSL

```bash
cd ~/projects/dincharya-ai
# Extract this ZIP to ~/projects/dincharya-ai/m2a
```

## 2. Create database (idempotent check)

```bash
docker compose exec -T postgres psql -U dincharya -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='dincharya_app'" | grep -q 1 || docker compose exec -T postgres psql -U dincharya -d postgres -c 'CREATE DATABASE dincharya_app;'
```

## 3. Create schema

```bash
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U dincharya -d dincharya_app < m2a/01_schema.sql
```

## 4. Seed once only (do not rerun or duplicate records)

```bash
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U dincharya -d dincharya_app < m2a/02_seed.sql
```

## 5. Verify

```bash
docker compose exec -T postgres psql -U dincharya -d dincharya_app -c "SELECT id,title,start_time,recurrence,weekdays FROM schedule_events ORDER BY start_time;"
```

## Notes
- Weekly weekdays use ISO numbering: Monday=1, Sunday=7.
- All times are in Asia/Kolkata.
- This is a provisional routine. It does not send reminders or edit the Telegram workflow.
- Before production, use a dedicated least-privilege database user, migrations, validation and backups.
