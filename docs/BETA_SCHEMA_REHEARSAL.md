# PR 18 personal schema rehearsal

## Accepted synthetic rehearsal and attended candidate

At `5bcda101bba4f10c1d87113da27e8f6ffc7b97b1`, Acer completed the native synthetic rehearsal with exit 0, all 15 checksums, signed relay and receipt checks, nine-table restore and unchanged inventory. The accepted four recurrence and nine historical tests carry forward. [Artifact decisions and attended candidate](ATTENDED_CANDIDATE.md) describe the offline preview renderer, remaining adapter work and separate owner gates. Earlier pending entries below document the historical sequence.

The first repository-owned migration is independent of the historical 0001–0015 chain. It runs transactionally on PostgreSQL 17 in the disposable database dincharya_beta_rehearsal and fixes the recipient to synthetic user 101. Discard the newly created rehearsal environment to roll back. Never run a down migration against an accepted database.

The signed adapter issues civil drafts and separate authenticated decisions. Date projection uses Asia/Kolkata and a rolling 400-day horizon. Restrictive function grants separate proposal, worker and evidence-backed operator actions. Receipt writes require a valid lease and a complete pair. Restore rotates the epoch, expires pending reviews and fences pending or in-flight delivery. Review the SQL and execute the native assertions before accepting these properties.

## Source disposition

| Artifact | Proposed scope |
| --- | --- |
| database/personal_beta/0001_civil.sql | Disposable rehearsal only. Review native privilege, lifecycle, receipt and recovery evidence before any personal-schema proposal. |
| dincharya/beta_dispatch.py and the civil parser | Synthetic signed gateway. No live bot transport. |
| beta_observer.py and beta_archive.py | Simulated alert transitions and local encrypted fixture archives. Off-site observation and off-device restore remain separate. |
| Existing pinned gateway, workflow and migrations | Retain the reviewed bytes and historical acceptance scope. |

## Signed relay checkpoint

At `31c5d9b7e2b12a77f455fd2040619c65ca191f8e`, Acer verified 14/14 source hashes, schema bootstrap and gateway role setup. The signed relay journey exited 1. Its precise failure is unknown. Cleanup and inventory passed; native SQL assertions and restore were not reached.

The diagnostic revision accepts an expected denial only on HTTP 403 or a relayed HTTP 200 with the exact denial object. A positive request still requires HTTP success and the expected application result. Work reproduced the former 403 handling mismatch offline. It does not establish which step failed on Acer. The rehearsal installer traces the inactive repository workflow through readiness, owner setup, creation and activation. The source-pinned staging installer is preserved.

## Browser-independent registration-race investigation

At approved `3409afad740dbcbbf9b3ee93d378eb211e93ea06`, one newly authorized
unchanged native rerun again failed `relay_forged_denial`, HTTPStatusError/404,
original exit 1; cleanup and complete Docker inventory comparison passed. The
15 source checksums matched before that run. No second full native run occurred.

A credential-free GET to the owner's localhost readiness endpoint returned HTTP 200.
No owner workflow, database or credentials were read. This instance is unrelated to
the harness's fresh relay container and cannot repair its cookies or registration.
The installer creates a fresh synthetic owner and retains its own httpx session cookie;
workflow creation and activation use that client, never the owner's browser session.

A separate fresh networkless n8n-only diagnostic reproduced the race: synthetic owner
setup/create/activate each returned 200; active=true and an active version were reported;
the immediate webhook POST returned 404/not registered. At subsequent three-second
probes the route was registered. Those later probes returned 500 because this diagnostic
intentionally used an unreachable downstream fixture; they are route evidence, NOT a
successful signed-application/native acceptance claim. The diagnostic container was removed.

The focused fix adds a bounded registration gate using only an empty invalid envelope
and invalid signature, which the dispatcher rejects before opening any database
connection. Retry only HTTP 404 during this readiness phase, at most 20 attempts with
0.25-second intervals and the client's existing timeout. Require exact denied body on
200 or 403; reject 401, other server errors or malformed denial responses immediately.
Registration timeout fails. Existing forged/foreign owner rejection, positive request,
approval replay and lifecycle assertions still execute separately; never retry valid
proposals, confirmations or mutations. Existing staging installer/workflow/business SQL
are unchanged. Add only the readiness label to the sanitized diagnostic allowlist.

Focused regression, diagnostics, security review and checksum results are recorded on PR #18. Native
acceptance remains FAIL at the approved base until a clean committed fix is reviewed and
its next single native run is authorized. Prior astronomy results are retained, not rerun.

## Readiness-fix security review

The uncommitted seven-file patch was reviewed against exact base
`3409afad740dbcbbf9b3ee93d378eb211e93ea06`, without repeating root-cause experiments.
No introduced credential or authorization risk was identified.

The source scanner reports one POTENTIAL_SECRET expression in each of two harness
files. Pattern/line comparison shows exactly the same matched source expression in
base and patch (line positions can shift). In the shell harness it is the SQL password
format placeholder; in the Python harness it is an environment lookup of the freshly
generated synthetic session password. These contain no embedded credential. Generation
uses fresh random material, not personal configuration; sensitive diagnostics stay
outside the mounted candidate and are removed by cleanup. This is explicit manual
false-positive review, not an automated scanner PASS. Scanner patterns, path rules,
allowlists and exit behavior remain unchanged. The checksum manifest's extension is
not a supported scanner input: validate it with sha256sum, not by bypassing its path rule.

The readiness probe sends only an empty invalid envelope and invalid signature and is
rejected before a database connection. At most 20 requests use the existing 15-second
client timeout and 19 quarter-second sleeps: bounded even when requests stall. Only
registration 404 is retried. Exact denied JSON on HTTP 200/403 is required; other status
codes, malformed bodies and exhausted registration attempts fail. Actual signed
acceptance actions have no automatic retry; pre-existing explicit replay assertions
are still deliberate independent test cases. No positive approval is used as a probe.

Seven relay/security tests and five diagnostic/cleanup tests pass, zero skips. Shell
and Python syntax, diff checks and all 15 designated source checksums pass. Four other
changed test/document files pass the source scanner. Business SQL, workflow and staging
installer are unchanged. No new native run after the fix is credited. The next task is
one scoped native rehearsal at the corrected clean committed SHA, using the existing
runbook, accepted PG17/application/n8n IDs and daemon, without repeating astronomy.
Keep the PR draft. No messaging, retained data, deployment or merge is authorized.

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

Record the exit code, stage markers, any allowlisted RELAY_FAIL substage/class/HTTP code, sanitized SQLSTATE/input line if available, and cleanup/inventory result on PR 18. Stop at the first failure. Do not submit SQL text, Docker logs, environment values or raw stderr. The previous astronomy results apply to this diagnostic-only revision. A successful native run requires the native, restore and cleanup PASS markers and exit zero.

## Evidence and release gates

Work ran 19 beta tests with zero skips, matched 16 prior source pins, validated the inert runtime plan, compiled Python and checked native shell syntax. Acer subsequently passed both astronomy suites. Native acceptance remains open. Prior Stage 1/2 runs do not qualify this schema. Persistent identity provisioning, status/worker supervision, independent host fencing, operator alert delivery, off-device backup verification, image adoption and a bounded owner-approved Telegram window remain release gates.

## Coordinator review correction

The previous rehearsal schema allowed arbitrary evidence and authorization identifiers. The replacement requires immutable positive evidence from the rehearsal fixture authority and a separately issued permit. The permit binds the operator OID, action, epoch, slot, observation, reason and evidence. The evidence binds the verified destination and message. The locked transaction checks expiry and writes one audit record. Exact replay is idempotent. Altered replay fails.

Use the scoped rerun above on the diagnostic revision. Verify all three full local image IDs independently against the accepted records before export. Record them with the test counts and exit status. The harness checks cleanup against the complete pre-run container/state, network, volume and image inventory on success and failure. Inventory differences require inspection, never automatic repair. The second database is on the same Docker daemon. Off-device restore and independent monitoring still require separate evidence.
