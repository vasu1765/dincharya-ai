# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint

Pre-merge review at committed/pushed head `43ad653`: GitHub reports MERGEABLE,
CLEAN, draft=true, no checks/review requirement shown. The merge UI is blocked
by draft status, not a demonstrated conflict. Review found one blocker: HTTP 429
ignored Telegram retry_after and entered ordinary short backoff. Local adapter
fix quarantines all 429s for manual recovery without changing migration checksums.
Regression reproduced before fix; all 15 focused reminder tests passed after.
No live test, credential access or Docker execution repeated. No other critical
PR-diff blocker found. See [pre-merge review](PR1_PREMERGE_REVIEW.md).
Acceptance evidence below was committed by the owner at `43ad653`; its old
uncommitted instructions are superseded by these commands for the new fix:

```bash
git diff -- dincharya/reminder_adapters.py tests/test_reminder_adapters.py telegram-gateway/README.md docs/HANDOFF.md docs/ROADMAP.md
git diff --no-index -- /dev/null docs/PR1_PREMERGE_REVIEW.md
git add -- dincharya/reminder_adapters.py tests/test_reminder_adapters.py telegram-gateway/README.md docs/HANDOFF.md docs/ROADMAP.md docs/PR1_PREMERGE_REVIEW.md
git commit -m "fix: quarantine Telegram rate limits instead of retrying early"
git push origin development/telegram-reminder
```

Git remains read-only in this sandbox; no commit/push attempted here. Current
remote head is not ready to merge until this tested fix is pushed. Then obtain
owner final merge approval and leave draft status; do not deploy or merge here.

2026-11-13: **PR #1 single live reminder acceptance passed** on
`development/telegram-reminder` at `aa05dd280ff6c90c510bc60c7351d1503a825cac`.
WSL Codex is primary while ChatGPT Work is paused. See the sanitized
[acceptance report](PR1_FOCUSED_ACCEPTANCE_RESULTS.md).

- Pinned daemon/image and disposable PostgreSQL 17 isolation verified. Only the
  exact owner-authorized schema file was loaded, unchanged. Approval/retry-cap
  SQL and concurrent decision/claim/acknowledgement passed. Lock-only harness
  timeout was corrected; only that check was repeated and passed.
- After explicit owner live-test authorization, a fresh tmpfs PostgreSQL database
  and dedicated network were used with only 127.0.0.1:55432 exposed. Dedicated
  test-bot identity and private credential-file permissions were verified without
  displaying credentials. Exactly one gateway poller started.
- Observed one pending proposal, null event ID and zero deliveries. Owner then
  sent `/approve_reminder 1` directly in Telegram; only then was one event created.
  Lock contention suppressed all attempts through due time plus 35 seconds.
  Disconnecting the lock holder allowed one acknowledged send: `sent`, attempts
  `1`, send timestamp present and worker token cleared. Ledger remained unchanged
  over two further ticks. Owner confirmed exactly one reminder in the test chat.
- Gateway stopped and lock reacquisition passed. Disposable container/network
  removed, loopback port closed, original running container IDs unchanged.
  Production credentials/services were never used. No deploy, merge or push.
- The owner's original private credential file remains outside Git; temporary
  gateway environment was stopped. Temporary acceptance virtualenv remains at
  `/tmp/dincharya-acceptance-venv`. Further Telegram sends require new authorization.

Local source/documentation changes remain uncommitted because Git metadata is
mounted read-only. Pre-existing untracked
`docs/WSL2_REMINDER_ACCEPTANCE_RESULTS.md` is preserved as historical blocked
results; it is superseded by the new report. No unrelated suites were repeated.
Documentation safety scan and diff checks passed. Keep PR #1 draft for final
review; remaining 2D/2E coverage is not declared complete. Message-ID persistence
remains a separate follow-up; it was not required to fix a demonstrated failure.
Sanitized evidence was posted to [PR #1](https://github.com/vasu1765/dincharya-ai/pull/1#issuecomment-6846033279).

Exact normal-WSL commands for the owner after reviewing the changes (the two
`--no-index` review commands return 1 when showing a new file):

```bash
cd /home/vasu1765/projects/dincharya-ai
git diff -- AGENTS.md docs/HANDOFF.md docs/ROADMAP.md docs/WSL2_REMINDER_ACCEPTANCE.md
git diff --no-index -- /dev/null scripts/prepare-acceptance-secrets.py
git diff --no-index -- /dev/null docs/PR1_FOCUSED_ACCEPTANCE_RESULTS.md
git add -- AGENTS.md docs/HANDOFF.md docs/ROADMAP.md docs/WSL2_REMINDER_ACCEPTANCE.md scripts/prepare-acceptance-secrets.py docs/PR1_FOCUSED_ACCEPTANCE_RESULTS.md
git commit -m "test: record successful isolated Telegram reminder acceptance"
```

Next: review PR #1 evidence and remaining 2D/2E gaps; do not repeat live acceptance,
merge, deploy or extend milestone scope without the applicable authorization.

## Last successful evidence

- Last full offline suite: **196 tests passed**. Final focused checkpoint: four
  migration-renderer tests and six reminder-worker tests passed; application
  runner, migration renderer and worker Python AST checks passed.
- **2C passed**, including final runner revision: verified pinned local Linux
  Docker Desktop identity; three healthy services; exact runtime isolation;
  synthetic application initialization; owner/bootstrap; non-Code imports;
  manual synthetic-pass; at least five successful scheduled outputs; n8n-only
  restart with PostgreSQL unchanged; at least three successful outputs started
  after restart readiness; no duplicate observed cadence slots; persistent durable
  job/occurrence identities and non-regressing clocks; retained legacy arrays.
- **2D/2E initial database integration passed** on the exact operator-authorized
  PostgreSQL schema: unchanged baseline bytes loaded into dincharya_app_test;
  both checksummed migrations applied; repeat migration application was a no-op;
  gregorian.sql and reminders.sql assertions passed. Baseline was not copied into
  Git and is not a production migration. Existing baseline functions are not
  collectively certified by these tests.
- Both successful runs verified teardown of test containers/network and unchanged
  original running container IDs. No production resources/data, real bot, Code
  workflow, production scheduler state or credentials were used.
- The last request to run expanded application checks was interrupted before any
  execution result/session was returned. Do not claim that rerun passed or started.
  No Docker was run during the final usage-preservation checkpoint.

## Runtime findings and scope

The exact image is n8n 2.47.3 with nodes-base 2.47.2. Default durable scheduling
intercepts Schedule Trigger rules and uses scheduled_job/scheduled_task state.
Legacy recurrenceRules/recurrenceRuleSignatures are preserved, but successful
retention does not prove they control the default runtime or historical engines.
The synthetic seven-minute rule is provisioned as a durable 420-second interval;
its full interval was not waited out. Fast emissions/restart were tested directly.

The create API drops supplied staticData (confirmed in API and test DB). Native
CLI import preserves it. CLI operations need a separate internal task-broker port
5680 beside server port 5679. Test n8n needs a bounded UID-1000 cache tmpfs; its
root filesystem remains read-only. API sessions are reused in private tmpfs to
avoid login rate limits and refreshed after restart when necessary.

Use only tests/integration/compose.json, project dincharya-m2c-synthetic,
--env-file /dev/null and integration profile. The runner pins local image IDs,
uses empty temporary Docker config/HOME and a fixed local socket, rejects remote
context/host overrides, and verifies the separately pinned daemon ID. Existing
test resources cause refusal. No published ports, persistent volumes, production
mounts or privileged containers. Cleanup is project-specific; forced termination
or daemon failure can still leave disposable resources.

## Implementation and unverified additions

- 0001_gregorian_occurrences.sql: strict proposal validation, daily/ISO-week/month/
  year matching, inclusive until dates, skipped invalid calendar dates, stable
  occurrence-date overrides/cancellations, series changes, stale proposal snapshots,
  authorized/idempotent decisions and explicit conflict override. Conflict review
  defaults to 730 days and is bounded to 3660; it is not proof of no conflicts for
  an infinite series. Overnight events remain unsupported.
- 0002_occurrence_reminders.sql: retain legacy ledger rows and event/date identity;
  materialize due work; claims/worker tokens/leases; definitive rejection retries
  with bounded backoff and five-attempt cap; uncertain outcomes/expired leases
  quarantined without automatic resend; bounded outage lookback (default six hours);
  preserve sent history; guard edits while a send is in flight.
- dincharya/reminders.py is an adapter-injected single-batch worker, tested offline.
  It opens no connections and performs no real Telegram I/O itself. Database and
  transport adapters and one-time gateway wiring now passed isolated acceptance.
  Operator resolution of uncertain sends and deployment remain future work.
  A batch abort can leave
  remaining claims to expire into quarantine; external exactly-once is not claimed.
- Parallel duplicate decisions, competing reminder claims and concurrent
  acknowledgement now passed multi-session acceptance. Checksum-corruption
  rejection remains source-reviewed/syntax-checked only; it was not rerun here.
- Five-attempt exhaustion and one-time gateway transport wiring now passed. Broad
  outage/recovery permutations, adversarial API cases, legacy API interaction and
  uncertain-send reconciliation still need coverage before closing all of 2D/2E.

## Source/provenance boundaries

Only the exact application-schema.sql path authorized in the conversation was
opened, read-only. No backup directory, n8n.dump, credential table or other backup
artifact was scanned. The three named repository docs identify **no exact original
review/provenance manifest path**. Manifest location remains missing; do not guess
or search private directories. The user's source authorization does not certify
all schema functions or authorize production application/source promotion.

Historical foundation checkpoint was `ceeba98`; the foundation commit
`b80a91d8` subsequently landed on main. 2C is complete for its synthetic scope.
2D and 2E remain partially complete.

Historical 2B evidence remains: four
current workflows, 94 history versions, two structural candidates; current and
published bodies remain separate; seven Code bodies were neither executed nor
cleared. No complete production workflow/schema baseline has been adopted in Git.

