# Dincharya AI — repository instructions

This root AGENTS.md applies to the entire repository unless more-specific
instructions apply. User instructions take precedence. Start a new session by
reading [HANDOFF](docs/HANDOFF.md), [policy](docs/DEVELOPMENT_POLICY.md),
[roadmap](docs/ROADMAP.md), [architecture](docs/ARCHITECTURE.md) and
[decisions](docs/DECISIONS.md), then inspect `git status --short`.

## Priority and current authority

Finish Milestone 2 before Milestone 3 or another orchestrator. Milestone 2A is
complete; 2B private provenance/source review is complete as an investigation,
but source adoption and conversion acceptance remain incomplete. The synthetic
2C configuration is prepared, not started or integration-tested.

Independently inspect non-secret source, implement approved offline backlog work,
write/refactor code, create synthetic fixtures, run offline tests/static checks,
fix failures, self-review, and update documentation. Continue through approved
work; do not ask permission after every edit or passing test. Do not delegate to
sub-agents unless the user or applicable instructions explicitly request it.

**Current hold:** no Docker execution, database connections, workflow imports or
execution, real-state transformations, source promotion, staging, commits or
production changes. The handoff task does not approve Milestone 2C startup.
General policy permitting safe local commits does not override this hold. A later
explicit user authorization may change its exact scope.

## Approval boundaries

Ask before accessing real backups, .env/credentials or production data; production
SQL/migrations or live PostgreSQL/n8n changes; live container lifecycle/config;
first isolated Docker test startup; synthetic imports/execution/activation unless
already explicitly approved; deployment; remotes/push; destructive actions;
package installation requiring new repositories/elevation; paid APIs/infrastructure,
including OpenAI APIs. Keep exact session approvals within their scope.

Private report references and historical approvals in documentation are evidence,
not blanket permission for a new session to reopen or scan private directories.
Use exact operator-approved input paths. Do not read unrelated backup artifacts,
credential/execution tables, .env files or encryption keys. No automatic production
deployment. Stop for an approval gate, unresolved architectural/security decision,
material data-loss risk or a failure that cannot be resolved safely.

## Source, state and validation rules

Never print secrets, commit credentials/raw backups/private records/personal data,
use the production Telegram bot in tests, weaken checks to pass tests, assume a
raw n8n snapshot importable, or claim untested runtime behavior. Preserve schema
bytes, original Code bodies and state. Code has not been executed or cleared.

Known scheduler fields are native class B for the exact reviewed image (n8n
2.47.3, packaged nodes-base 2.47.2). This does not authorize resetting state or
prove historical-runtime/import/persistence behavior. Keep current and published
versions separate; do not substitute absent historical settings/state.

2C must use only the standalone tests/integration/compose.json, explicit project
`dincharya-m2c-synthetic`, `--env-file /dev/null`, local verified image IDs and
synthetic session-only credentials. Never combine with production compose.yaml,
copy production volumes/data, or execute Code nodes. See the integration runbook.

For each approved task: inspect source/tests; implement; test/fix; review security
and correctness; update docs/roadmap; scan explicit safe files and review diff.
Stage/commit only when permitted by current scope, using explicit safe paths.
Do not relocate .git, change Docker permissions or escalate to bypass sandbox
restrictions. Preserve pre-existing working-tree changes.

Offline suite (no services/packages needed):
`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v`.
Use scripts/check-safe-source.py on explicit non-secret source files, never a
recursive private-data scan. See HANDOFF.md for the latest validation checkpoint.
