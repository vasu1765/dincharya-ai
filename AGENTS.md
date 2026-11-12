# Dincharya AI development instructions

Read docs/DEVELOPMENT_POLICY.md and docs/ROADMAP.md before work. Finish all of
Milestone 2 before starting Milestone 3 or another orchestrator.

Stack: Ubuntu WSL2, PostgreSQL 17, n8n in Compose, Python Telegram gateway,
Ollama/Qwen2.5 3B; application timezone Asia/Kolkata. Future deployment is an
India-based VPS. Planned orchestrators: Dincharya, Adhyayan, Arogya,
Atma-Chintan, Vittiya. See the roadmap for scope and dependencies.

Independently inspect non-secret source, implement approved backlog work, refactor,
write synthetic fixtures/tests, run offline checks, fix failures, self-review,
update docs/roadmap, and make safe local Git commits after tests and secret checks.
Continue through approved work; do not ask permission for routine source edits.

Ask before reading real backups, .env/credentials or production data; executing
production SQL/migrations; modifying live PostgreSQL/n8n; starting/stopping or
reconfiguring live containers; first creating/running isolated Docker test
environments; deploying; creating/pushing remotes; destructive commands; paid
API/infrastructure use. Do not use paid OpenAI APIs without approval.

Never print secrets, commit credentials/raw backups/personal data, weaken security
checks to pass tests, use the production Telegram bot in tests, assume a raw n8n
snapshot is importable, claim untested features work, or automatically deploy.

For each approved task: inspect source/tests; implement; test and fix; review
security/correctness; update documentation and roadmap; inspect the proposed Git
diff and run secret checks; commit only explicit safe paths locally; continue to
the next approved task. Stop for approval gates, unresolved architectural choices,
material security/data-loss risk, or failures that cannot be resolved safely.
Do not infer approval of gated work from a roadmap checkbox.

Current approved implementation scope: complete Milestone 2A offline hardening
and tests. Real inputs, production access, and first container tests remain gated.
No sub-agent delegation is requested by these instructions.

Use stdlib offline checks first:
`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v`.
Keep generated candidates and private provenance outside Git. See the source
synchronization runbook for review boundaries. Record validation limits honestly.
