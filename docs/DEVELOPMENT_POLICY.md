# Development policy

Dincharya AI is a personal Telegram assistant running on Ubuntu WSL2 with
PostgreSQL 17, n8n/Compose, Python, and local Ollama Qwen2.5 3B. Keep Asia/Kolkata
semantics explicit. Planned domains and phase order are in ROADMAP.md.

## Authority and boundaries

Approved source work is autonomous: inspect non-secret files, implement/refactor,
create synthetic fixtures, run offline tests/linters/static checks, fix failures,
self-review, update docs/roadmap, and commit validated safe changes locally.
Do not stop after individual edits or passing tests. Continue approved backlog
tasks until an approval gate or genuine blocker is reached.

Ask before real backup, credential/.env or production-data access; production
SQL/migrations or live workflow/database changes; live container lifecycle or
configuration changes; first isolated Docker environment creation/execution;
VPS deployment; remote creation/push; destructive actions; or paid APIs and
infrastructure, including OpenAI APIs. Existing approvals persist within scope.
Unresolved architecture or material security/data-loss risks require a decision.

Never print secrets or commit credentials, backups, personal data, or private
provenance. Never use the production bot for tests, bypass checks to pass a suite,
assume raw snapshots importable, claim unsupported test evidence, or auto-deploy.

## Delivery loop

1. Inspect relevant source/tests and the current Git state.
2. Implement small coherent changes in the approved scope.
3. Run appropriate offline tests/static checks and fix failures.
4. Review correctness, sensitive-data boundaries, and failure paths.
5. Update documentation, acceptance evidence, and roadmap.
6. Scan only explicit safe candidate files; inspect Git diff/index. Never read
   .env or private inputs as part of repository-wide scanning.
7. Stage explicit paths and commit locally. Do not stage another person's changes
   or generated candidates; do not create/push remotes. If metadata is sandbox
   read-only, report the failure rather than escalating or relocating .git.
8. Continue approved work. Stop before the next gated operation.

## Source and test safety

Source-preparation outputs are unencrypted private review candidates outside all
Git repositories. Unix mode 700/600 does not protect from host/Windows
administrators or physical disk access. Human review is required because scanners
cannot establish absence of secrets. Promotion into Git is a separate explicit
review operation, not a preparation side effect.

Preserve schema bytes; never silently rewrite SQL bodies/triggers. Inventory,
function signatures, schema completeness, permissions, and runtime compatibility
need separately approved isolated PostgreSQL tests. Keep n8n's internal migrations
separate from application migrations. Keep draft/published claims explicit and
unverified unless evidence supports them. Inactive JSON is not a network sandbox.

Offline tests use only synthetic data and temporary directories. Docker test
configuration must be standalone, with distinct project/network/volumes, no
production secrets, ports, polling, or external calls. Approval is required before
first use. Keep production configuration unchanged during source-only work.
