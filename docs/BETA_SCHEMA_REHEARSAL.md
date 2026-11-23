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

## One Acer WSL Codex task

Use a clean detached worktree at the exact PR head supplied with this task. Export REV to that full SHA. Use the previously accepted local PG17, staging Python and n8n image IDs as PG, APP and N8N respectively. Use the accepted astronomy interpreter as ASTRO_PYTHON and the reviewed public kernel path as DINCHARYA_PUBLIC_DE440S. Resolve these from public dependency records and local image metadata only. Stop if any pin is unavailable. Use no existing service, private configuration or retained volume.

```bash
set -eu
test "$(git rev-parse HEAD)" = "$REV"
test -z "$(git status --porcelain)"
test -r "${DINCHARYA_PUBLIC_DE440S:?pinned public kernel}"
sha256sum --check docs/beta-schema-rehearsal.sha256
"$ASTRO_PYTHON" -B -m unittest discover -s tests -p test_recurring.py -v
"$ASTRO_PYTHON" -B -m unittest discover -s tests -p test_historical_panchang.py -v
bash tests/integration/beta_native.sh
```

Require four recurrence tests, all historical tests with the pinned kernel, zero skips and native exit 0. Capture the first failing assertion if any. Record the SHA, disposable image IDs, counts and sanitized outcomes on PR 18. The native runner uses an internal-only n8n network and fresh PG tmpfs, records simulated approvals and lifecycle changes, exercises receipts and operator reconciliation, and compares seven tables after encrypted dump restoration to a second, networkless PG instance.

## Evidence and release gates

Work ran 19 beta tests with zero skips, matched 16 prior source pins, validated the inert runtime plan, compiled Python and checked native shell syntax. The two astronomy-dependent suites and native runner await Acer execution. Prior Stage 1/2 runs do not qualify this schema. Persistent identity provisioning, status/worker supervision, independent host fencing, operator alert delivery, off-device backup verification, image adoption and a bounded owner-approved Telegram window remain release gates.
