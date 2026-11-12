# Dincharya AI — quick handoff

Read root [AGENTS.md](../AGENTS.md) first, then [roadmap](ROADMAP.md),
[policy](DEVELOPMENT_POLICY.md), [architecture](ARCHITECTURE.md) and
[decisions](DECISIONS.md). Finish Milestone 2 before Milestone 3.

**STOP boundary:** 2C is prepared, not authorized to start. No Docker, DB
connections, imports/execution, real-state changes, staging/commits, source
promotion or production operations in the current scope. Historical private-file
authorizations are not blanket permission for a new session.

## Verified checkpoint

- Stack: Python Telegram polling, n8n/Compose, PostgreSQL 17, local Ollama/Qwen2.5
  3B, Ubuntu WSL2, Asia/Kolkata. Production Compose and gateway were not changed.
- 2A complete; Git HEAD 62e96e6 records its tooling. Later 2B/C work includes
  uncommitted/untracked files. Inspect status; do not reset/clean or assume Git
  contains all local work. No changes are staged at this checkpoint.
- 147 offline tests pass. No container integration tests/imports have run.
- Private 2B evidence: four current workflows, 94 historical versions, one resolved
  current published reference and 11 resolved historical event/version references.
  Current nodes/connections match same-version history. Current/published differs
  only in one node's position; settings/state/history runtime remain unverified.
- Two current structural candidates pass; two remain losslessly archived behind
  native-state/Code acceptance gates. No complete production baseline is adopted
  in Git. m2a/ is historical and must not be replayed.
- Verified exported n8n 2.47.3 includes nodes-base 2.47.2. recurrenceRules and
  recurrenceRuleSignatures are native class-B cadence/signature state, preserved
  unchanged. Manual execution bypasses filtering. Import/restart persistence and
  historical compatibility are not proven. See [state review](native-scheduler-state.md).
- Seven Code bodies were not executed or cleared. The bracket warning was returned
  array literals, not computed property access. Static review is not clearance.

Private manifest evidence was rechecked for this handoff. Raw records, identifiers,
source hashes and detailed reports stay outside Git. Some reports are temporary
/tmp artifacts: obtain exact operator-approved paths if needed; do not scan backups
or reopen .env/credentials. Do not copy private evidence into documentation.

## Next actions

1. Run `git status --short` and
   `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v`.
2. Request explicit approval for only the disposable 2C startup/teardown, synthetic
   DB initialization and supplied non-Code imports/executions/activation/restart
   tests. Do not interpret this handoff as that approval.
3. Follow [integration runbook](../tests/integration/README.md): standalone
   tests/integration/compose.json, project dincharya-m2c-synthetic,
   --env-file /dev/null, profile integration, verified local IDs, generated test
   secrets. No production data, ports, polling, credentials or volumes.
4. After approval, verify health/isolation, bootstrap a synthetic owner/project if
   needed, run inactive manual smoke, then synthetic state-import/activation tests.
   Restart only n8n-test with PostgreSQL alive; teardown loses tmpfs data.
5. Record runtime evidence before resolving conversion acceptance/source adoption.
   Do not begin advanced recurrence or Panchang yet. Update roadmap/docs after work.

For this checkpoint, syntax/JSON, source secret scans, whitespace and private
manifest checks passed. They do not prove Compose startup, SQL correctness,
workflow importability, exactly-once reminders or recovery readiness.
