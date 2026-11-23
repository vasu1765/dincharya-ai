# PR 18 personal schema rehearsal

The first repository-owned migration is independent of the historical 0001–0015 chain. It runs transactionally on PostgreSQL 17 in the disposable database dincharya_beta_rehearsal and fixes the recipient to synthetic user 101. Discard the newly created rehearsal environment to roll back. Never run a down migration against an accepted database.

The signed adapter issues civil drafts and separate authenticated decisions. Date projection uses Asia/Kolkata and a rolling 400-day horizon. Restrictive function grants separate proposal, worker and evidence-backed operator actions. Receipt writes require a valid lease and a complete pair. Restore rotates the epoch, expires pending reviews and fences pending or in-flight delivery. Review the SQL and execute the native assertions before accepting these properties.

## Source disposition

| Artifact | Proposed scope |
| --- | --- |
| database/personal_beta/0001_civil.sql | Disposable rehearsal only. Review native privilege, lifecycle, receipt and recovery evidence before any personal-schema proposal. |
| dincharya/beta_dispatch.py and the civil parser | Synthetic signed gateway. No live bot transport. |
| beta_observer.py and beta_archive.py | Simulated alert transitions and local encrypted fixture archives. Off-site observation and off-device restore remain separate. |
| Existing pinned gateway, workflow and migrations | Retain the reviewed bytes and historical acceptance scope. |

## Single scoped Acer native rerun

The Acer run at `a05e1484ef364e50568c33318ace8aa70aaf4ec4` passed the manifest and all four recurrence and nine historical tests with zero skips. Native execution exited 3. The failing stage and SQLSTATE were not captured. Cleanup reported no labelled leftovers or inventory mismatch. Those observations do not identify a failed SQL statement.

In Acer WSL Codex use a fresh, clean detached worktree at the exact revision in the PR diagnostic handoff. Export that SHA as REV. Reuse the independently verified, previously accepted full local PG, APP and N8N image IDs and the pinned daemon. Run only:

```bash
set -eu
test "$(git rev-parse HEAD)" = "$REV"
test -z "$(git status --porcelain)"
sha256sum --check docs/beta-schema-rehearsal.sha256
bash tests/integration/beta_native.sh
```

Record the exit code, stage markers, sanitized SQLSTATE/input line if available, and cleanup/inventory result on PR 18. Stop at the first failure. Do not submit SQL text, Docker logs, environment values or raw stderr. The previous astronomy results apply to this diagnostic-only revision. A successful native run requires the native, restore and cleanup PASS markers and exit zero.

## Evidence and release gates

Work ran 19 beta tests with zero skips, matched 16 prior source pins, validated the inert runtime plan, compiled Python and checked native shell syntax. Acer subsequently passed both astronomy suites. Native acceptance remains open. Prior Stage 1/2 runs do not qualify this schema. Persistent identity provisioning, status/worker supervision, independent host fencing, operator alert delivery, off-device backup verification, image adoption and a bounded owner-approved Telegram window remain release gates.

## Coordinator review correction

The previous rehearsal schema allowed arbitrary evidence and authorization identifiers. The replacement requires immutable positive evidence from the rehearsal fixture authority and a separately issued permit. The permit binds the operator OID, action, epoch, slot, observation, reason and evidence. The evidence binds the verified destination and message. The locked transaction checks expiry and writes one audit record. Exact replay is idempotent. Altered replay fails.

Use the scoped rerun above on the diagnostic revision. Verify all three full local image IDs independently against the accepted records before export. Record them with the test counts and exit status. The harness checks cleanup against the complete pre-run container/state, network, volume and image inventory on success and failure. Inventory differences require inspection, never automatic repair. The second database is on the same Docker daemon. Off-device restore and independent monitoring still require separate evidence.
