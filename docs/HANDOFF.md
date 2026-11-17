# Dincharya AI — handoff

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint — M2H Cycle 6 historical Panchang and source review

[Cycle 6](M2H_CYCLE6_HISTORICAL.md) records the historical query and anniversary
flow, public comparisons, isolated operations and the single WSL exact-schema
follow-up. The [2B review package](M2B_SOURCE_ADOPTION.md) is the owner-approved
alternative process. Artifact adoption requires a separate reviewed decision.
Current/published workflow lineage and original schema acceptance are preserved.

## Prior checkpoint — M2H Cycle 5 recurrence and notifications

Review [Cycle 5 behavior, test commands and the completion matrix](M2H_CYCLE5_RECURRENCE.md).
The branch adds isolated controls and notification slots on top of PR #8.
Existing manual rules and legacy delivery history are preserved. Restore coverage
uses a separate database in one disposable cluster. Before promotion, repeat
compatibility on the authorized schema with the new migrations, complete the
cross-cluster restore and supervised recovery exercises, resolve 2B provenance
and broaden the lunar calendar evidence. Live activation needs owner approval.

## Prior checkpoint — M2H Cycle 4 application and operations

Exact authorized schema acceptance now **PASSED (exit 0)** in the original WSL
checkout on `development/m2h-operational-acceptance`, following a diagnostic
failure and smallest launcher correction: convert the Unix socket `Path` to a
string. Fixed stage labels expose no exception/SQL/credential/private-path
contents. Schema bytes and migration assertions remain unchanged.

Actual evidence: migration ledger/reapplication, scoped calculator permissions,
native n8n relay, real SDK with simulated Telegram, owner approvals/foreign and
duplicate rejection, annual restart/stale/expiry/cancellation/identity checks,
one reminder row, teardown and unchanged unrelated container inventory passed.
See [scope and results](M2H_CYCLE4_OPERATIONS.md#actual-focused-rerun-result).
No broader restore/delivery matrix was rerun or newly credited on this baseline.

Offline: 2 new launcher tests + 39 existing runner tests passed; AST/diff checks
passed. A supplementary annual/application unit run stalled at sandbox executor
shutdown and was stopped (143), not credited. Source scan passes for changed
launcher/diagnostic test/M2G runner; the shared runner has a pre-existing scanner
rejection in both HEAD and working tree; its fixed diagnostic additions were
manually reviewed. No scanner policy was weakened. Production, real Telegram,
2B source adoption, advance slots and scheduling enablement remain gated.

Git metadata remains read-only. Exact safe-file commit in normal WSL:

```bash
git branch --show-current
git diff --check
git add -- tests/integration/runner.py tests/integration/m2g_runner.py tests/integration/m2h_baseline_acceptance.py tests/test_m2h_baseline_diagnostics.py docs/M2H_CYCLE4_OPERATIONS.md docs/HANDOFF.md
git diff --cached --check
git diff --cached
git commit -m "fix: diagnose Cycle 4 stages and correct Unix socket startup"
git push origin development/m2h-operational-acceptance
```


[Cycle 4](M2H_CYCLE4_OPERATIONS.md) verifies native n8n 2.47.3 with disposable
PostgreSQL 17.12, the repository schema fixture and simulated Telegram. The
report records restart, reminder recovery and same-cluster restore evidence.
The exact previously authorized schema command now passes in WSL. The
2B original provenance manifest remains unresolved. Live lunar scheduling
stays disabled.

## Prior checkpoint — M2H Cycle 3 annual development review

[Cycle 3](M2H_CYCLE3_ANNUAL.md) adds durable annual rules, per-year owner
approval, restart and expiry recovery, and reviewed cancellation. Reuse the
standalone disposable acceptance harness with the pinned public ephemeris.
For the next acceptance stage, use an exact separately authorized schema-only
baseline and the real isolated n8n relay with Telegram simulated. The original
2B provenance manifest path remains unknown. Production and real Telegram
remain outside this checkpoint.

## Prior checkpoint — M2H Cycle 2 development review

[Cycle 2](M2H_CYCLE2_TELEGRAM.md) adds bounded English, Hindi and Hinglish lunar
proposals and two explicit owner approvals. The integration harness uses the
real Telegram SDK and a disposable PostgreSQL 17 cluster, with Telegram and
the signed n8n relay simulated. Preview expiry, stale review and duplicate
approval protections are covered. No WSL handoff or real Telegram run is needed
for this checkpoint. Production scheduling and reminder delivery stay disabled.

## M2H Cycle 1 owner policy

[The Cycle 1 report](M2H_CYCLE1_ACCURACY.md) records the owner-approved Drik Delhi
primary and IMD PAC secondary profiles, the 90-second publisher diagnostic
and the 300-second sunrise guard. Himalayan Academy remains historical
evidence outside the primary denominator. The guarded selector withholds
model disagreements, conflicting comparable Delhi labels and uncertain dates.
Production lunar scheduling remains disabled.

## Prior checkpoint — M2G private Telegram acceptance PASSED

Clean entry at pushed `6848d4f2b7a1bbbb6d61c0bbf162bf6f05bebd4d` on
`development/m2g-telegram-integration`. Owner explicitly authorized ONE real
synthetic birthday reminder to the owner's private chat via the dedicated test
bot, fresh disposable PostgreSQL/n8n and separate Telegram rule/occurrence approvals.
The earlier29-file implementation is committed; those commands are obsolete.

- Existing tested launcher/application reused exactly; no rebuild or synthetic
  suite rerun. Hidden local credential input; file/owner/600 and parent700 checks
  passed without printing/committing values. Dedicated bot identity verified.
- Approved daemon44c1ef83-c50e-4ecc-8f19-4b112bc40f29, pinned fresh three-service
  isolation and named schema-only baseline verified. No other backup/private2B
  input or production service/credential accessed.
- Owner confirmed BOTH explicit approvals. Read-only observations verified one
  rule/occurrence/projection/series; no attempt before the approved fixture time.
- **One real reminder delivered, attempts1, one paired acknowledgement receipt.**
  Owner explicitly confirmed exactly one reminder received. More than two extra
  polling intervals (at least77 seconds) retained one delivery/attempt/receipt;
  no failures or uncertain outcomes, no duplicate or replacement request.
- Gateway exited0 gracefully before launcher STOP. Launcher final checks passed
  exactly one acknowledged delivery/series; exited0 and confirmed full disposable
  teardown plus unchanged unrelated running-container IDs.
- No code fix, reset, blind resend, production, deployment, merge or astronomy
  enablement. [Sanitized actual evidence](M2G_TELEGRAM_RESULTS.md) and GitHub issue2
  updated. No raw IDs/messages/credentials/runtime paths stored in repository.

This one-reminder authorization is consumed/completed; another real test/send
requires new explicit approval. General calendar/astronomical adoption, advance
slots,2B provenance and broader operational/VPS acceptance remain pending. No
other orchestrator. Restricted original credentials remain outside Git; temporary
runtime configuration/roles/sockets were removed with the disposable environment.

Git metadata remains read-only; only these two documentation files are modified.
Source-safety/link/diff and application-source immutability checks pass. Normal WSL:

```bash
git branch --show-current
git status --short
git diff --check
git add -- docs/M2G_TELEGRAM_RESULTS.md docs/HANDOFF.md
git diff --cached --check
git diff --cached
git commit -m "docs: record successful M2G private Telegram acceptance"
git push origin development/m2g-telegram-integration
```

## Prior integration evidence (historical)

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

