# Dincharya AI — repository instructions

This root AGENTS.md applies to the entire repository unless more-specific
instructions apply. User instructions take precedence. Start a new session by
reading [HANDOFF](docs/HANDOFF.md), [policy](docs/DEVELOPMENT_POLICY.md),
[roadmap](docs/ROADMAP.md), [architecture](docs/ARCHITECTURE.md) and
[decisions](docs/DECISIONS.md), then inspect `git status --short`.

## Coordination and approvals

ChatGPT Work owns implementation, architecture, development branches, PRs,
review, focused verification and planning. GitHub is the shared source of
truth. Read the active PR and its latest evidence before choosing the next
task. Preserve existing work. Use WSL Codex only for essential local execution.
Put one executable task in the development branch and return sanitized results
directly to the same PR. Keep AGENTS.md and docs/HANDOFF.md current.

Deliver the first owner-approved Telegram reminder through draft PR #1, then
close 2D/2E before starting another milestone. Make routine decisions, fixes
and development-branch commits autonomously. Ask the owner before major
architecture changes, production access, deployments or merging to main.
Use only exact authorized private inputs and dedicated test credentials.
Never read production credentials or modify production services without
explicit approval. Preserve existing acceptance checks and security boundaries.

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

For each development task: inspect source/tests; implement; test/fix; review security
and correctness; update docs/roadmap; scan explicit safe files and review diff.
Stage and commit explicit safe paths on the development branch.
Do not relocate .git, change Docker permissions or escalate to bypass sandbox
restrictions. Preserve pre-existing working-tree changes.

Offline suite (no services/packages needed):
`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v`.
Use scripts/check-safe-source.py on explicit non-secret source files, never a
recursive private-data scan. See HANDOFF.md for the latest validation checkpoint.
