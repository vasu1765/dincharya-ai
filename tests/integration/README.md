# Milestone 2C synthetic integration environment

Prepared only. No Docker command, database connection or workflow import has been
run by Codex. First startup, synthetic DB initialization, imports/executions and
teardown require explicit approval. No production backup/schema/workflow is used.

## Isolation contract

compose.json is JSON-compatible Compose syntax and is a standalone file, never
an override of production compose.yaml. Use project dincharya-m2c-synthetic,
--env-file /dev/null, --profile integration and an explicit -f path. No production
.env or credentials are loaded. Images must be administrator-verified local IDs;
pull_policy=never prevents registry downloads. The n8n image must match the
reviewed 2.47.3 build. No tag/nearby release substitution is allowed.

Three separate containers: postgres-test, n8n-test, mock-services. Only a new
internal project network is attached. No host ports, external networks, live
volumes, Docker socket, privileged mode or Telegram polling gateway are present.
Runtime data is tmpfs; mounts are limited to read-only synthetic repository files.
PostgreSQL has two fresh test databases: dincharya_n8n_test for n8n metadata and
dincharya_app_test for synthetic events. Production database names are not targets.
The PostgreSQL initializer and n8n's own migrations affect only these disposable
containers. Test-generated passwords and encryption key are required in process
environment, not stored in Git or .env files, and must never be printed.

The n8n/mock services run UID/GID 1000 with no capabilities. Confirm that UID is
appropriate for the approved image before first startup. PostgreSQL retains its
image's normal initialization privileges inside the new container so it can
initialize its tmpfs; no privileges or writes are granted to host data. Services
have bounded memory/CPU, no automatic restarts, and read-only root filesystems.

The internal mock supplies /health, /counts, /telegram/sendMessage and
/ollama/api/chat. It makes no outbound calls, stores only request counts, limits
request sizes/timeouts and does not log payloads. It is a synthetic protocol stub,
not a claim of real Telegram/Ollama compatibility. The real Telegram node cannot
be redirected simply by setting this URL; do not attach real bot credentials.
No workflow uses real Telegram/Ollama endpoints or any Code node.

## Future approved startup

The following is a recipe for a later approved session, not an action performed
by documentation. Use only verified full local image IDs, not the literal
placeholders. Never run docker compose config with resolved secret values.

```bash
cd ~/projects/dincharya-ai
export DINCHARYA_TEST_POSTGRES_IMAGE='sha256:ADMIN_VERIFIED_POSTGRES_17_IMAGE_ID'
export DINCHARYA_TEST_N8N_IMAGE='sha256:ADMIN_VERIFIED_N8N_2_47_3_IMAGE_ID'
export DINCHARYA_TEST_DB_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export DINCHARYA_TEST_ENCRYPTION_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
docker compose --env-file /dev/null -p dincharya-m2c-synthetic \
  -f tests/integration/compose.json --profile integration up -d
```

Command substitution captures generated test secrets; do not echo them or enable
shell tracing. Keep the same private test-session values for controlled restarts.
Do not copy production .env, encryption keys, credentials, or volumes. Inspect
only service health and allowlisted metadata, never dump resolved environments.
Local image availability, Compose compatibility, permissions, resource headroom,
and health endpoints remain runtime checks, not established by static tests.

## Approved test checkpoints

1. Confirm only the three test services and the new internal network exist; no
   host bindings/production mounts. Verify health without printing credentials.
2. Query only synthetic_events in dincharya_app_test and inspect test n8n readiness.
   Configure any fresh owner/project with generated synthetic credentials only.
3. With explicit synthetic-import/execution approval, import inactive manual-smoke
   and check its Set output. No API key/owner from production may be used.
4. Inspect synthetic scheduler-state import handling before activation; record
   which fields n8n preserves. Only after synthetic-activation approval, observe
   native interval filtering/re-arming and emitted outputs on the isolated stack.
   Never insert real workflows or Code nodes into this stack.
5. For persistence tests restart only n8n-test while postgres-test stays running.
   Restarting PostgreSQL or taking the stack down loses its tmpfs data. Record
   engine persistence/import behavior; do not infer it from node-source review.
6. After approved teardown, use the same explicit file/project/profile and down
   (no broad prune or production Compose commands). Clear generated host variables.

There is no automatic importer or workflow executor in the configuration. The
synthetic scheduler fixture remains inactive until an approved test explicitly
activates it. Its values are invented test data, not copied production state.
Existing unit tests validate isolation contracts, JSON fixtures, source hashes and
state preservation without executing Docker or JavaScript workflow code. Native
runtime behavior, imports, restart persistence, mock protocol interactions and
complete migration/source compatibility are not yet integration-tested.
