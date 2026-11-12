# Offline tests

Run from the repository root, without packages or services:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
```

Fixtures are invented. Tests write only to temporary directories. They do not
read .env, backups, credentials, or production databases.

`compose.test.yaml` is future test scaffolding, not executed by the suite. It has
no host ports, production mounts, persistent volumes, credentials, gateway, or
n8n service. PostgreSQL uses trust authentication on a dedicated internal network
and ephemeral tmpfs. Never attach another workload or publish its port. It still
consumes host resources and is not a security boundary against a host administrator.

After separate approval to start test containers, use only this standalone file:

```bash
docker compose -p dincharya-phasea-test -f tests/compose.test.yaml --profile test up -d
docker compose -p dincharya-phasea-test -f tests/compose.test.yaml --profile test down
```

Do not merge it with production Compose. Pin an approved PostgreSQL 17 digest and
verify compatibility before relying on integration results. No container commands
were run while implementing Phase A.
