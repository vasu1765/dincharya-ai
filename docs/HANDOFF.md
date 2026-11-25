# Dincharya AI — handoff

## CONNECT gateway delta

PR #18 retains the accepted e3518726 runtime. The candidate binds username and upstream IP to the manifest, uses explicit CONNECT with end-to-end TLS and verifies namespace output rules and a four-container topology. Work passed 26 focused tests. The [single isolated Acer test](ATTENDED_CANDIDATE.md#one-acer-task-for-this-delta) remains pending. Obtain separate live approval after review.

Acer verified all nine source hashes and passed eight focused CONNECT tests at
`0d74512f6a56d6d14ccc3a27b5d088ab3c07eb1a`. After nftables installation the native
runner exited 255 before loading any policy. A separate isolated probe reproduced
the exact error from `ip link set up netns PID`: iproute2 read `up` as the state
flag and reported a missing device. The harness now names the interface
`uplink0`, supplies explicit `dev` arguments and records the stage and original
status on failure. A targeted replay moved and activated both veth ends and
reaped the child namespaces. No CONNECT runner or gateway process remained
visible after the reported failure. The original scratch directory was not
retained for independent inspection.

The run at `3234ef93e1354f1ddc8114bf07e0c3caa4f09275` passed veth setup and
the alternate-port positive control. App nftables load succeeded. Readback
exited 1 and cleanup passed. With `nft -nn`, the installed nftables prints
`ct direction 1` for the rendered `ct direction reply`. The verifier now uses
`nft -s -y` to preserve the symbolic conntrack direction and numeric hook
priority. The exact comparison and rules remain unchanged. The focused
regression passed. A synthetic namespace test verified real readback for all
four roles and confirmed the verifier rejects an added accept rule for each.

The corrected full namespace run is pending a clean committed revision and
interactive sudo. Require both policy readbacks, TLS through CONNECT,
destination denials, cleanup and exit 0 before staging daemon-host topology.
All earlier accepted suites carry forward.

## Final runtime candidate

The corrected operator working tree passed on Acer with exit 0, six receipt pairs and unchanged inventory. The current source isolates astronomy from Telegram TLS and adds image, CA, host and environment checks. Work passed 18 focused tests. The clean committed CLI journey is pending. Use the [single Acer task and owner authorization template](ATTENDED_CANDIDATE.md#final-attended-runtime-candidate).

## PR #18 operator runtime diagnosis

The operator run at `75d0155a2607665a47fe88315a4988be0f000b4f` exited 1.
A focused disposable diagnostic verified n8n activation, webhook readiness,
one-use approval consumption and the first signed echo. The calculator then
rejected the image's certifi 2026.10.23 because the astronomy lock requires
2025.10.5. The older relay forwards a signed request to its dispatcher.
The operator relay verifies a single matching signed echo before local
dispatch. Both use the same webhook installation and denial probe.

The recording fixture now verifies the public certifi wheel against the
existing astronomy artifact hash and stages it on the disposable Python
import path. Diagnostics report fixed stages, error class, HTTP status when
available and allowlisted source locations. The live launcher does not use
this overlay. Before live review, pin a runtime that satisfies the
astronomy dependency lock and has reviewed Telegram TLS trust.

The corrected working-tree diagnostic exited 0 on Acer with the pinned
PG17, application and n8n images. It verified a historical reply, two previews,
two confirmations and one reminder, with all six receipt pairs in order.
A second startup with the consumed approval was rejected without sending.
Cleanup and the container, network, volume and image inventory comparison
passed. All 12 focused operator tests and six source checksums passed.
The source scanner still flags identical pre-existing credential patterns
in the two harness files.

The six adapter cases passed earlier at
`86d4a69b77c6c429a9408658243ff9de3d28209c`. Retain that result and the earlier
astronomy and synthetic native evidence at their accepted revisions.
See [the operator runbook](ATTENDED_CANDIDATE.md#operator-acceptance).
Keep PR #18 draft and obtain separate authorization for a live session.

## PR #18 attended appointments timing failure diagnosed; focused correction passes

At candidate `c8b981d46d7933c042a8bd77a40d049f7c6ed730`, the six source
checksums passed and the native task first failed in `appointments_journey`.
The failure was isolated in fresh disposable PG17 diagnostics:

- The origin-ID, token and preview-message bot-identity negative checks were
  correct and passed; the bot/owner callback checks are unchanged.
- The final delivery assertion saw four sent preview/decision messages and no
  reminder attempt. PostgreSQL showed one confirmed reminder appointment was
  still two seconds in the future when the worker tick ran. The fixture had
  waited using the application container clock plus 300 ms. It now waits on
  PostgreSQL `clock_timestamp()` with a bounded timeout and a 55-second lateness
  guard within the unchanged one-minute due window.

Added fixed-label, secret-safe journey diagnostics and focused tests. Results:
4 timing tests, 11 gateway tests and 2 preview tests passed; syntax checks
passed. The appointments-only isolated scenario passed with 5 attempts, 5
paired sends, 1 reminder, 2 confirmed appointments and 0 uncertain deliveries;
cleanup and the complete Docker inventory comparison passed. No business SQL,
gateway authorization, advisory locks, lease/receipt settlement or delivery
policy changed. The updated eight-entry source manifest verifies. The other
five native scenarios remain pending.

The explicit source scanner rejected both the baseline and modified
`attended_delta.py` and `attended_delta.sh` inputs. These are the same existing
generated-password environment/SQL-transfer patterns; no credential values
are embedded or printed. The new timing helper, its tests, and both gateway
modules passed the scanner. The scanner was not modified or bypassed.

This correction is in the detached worktree only. Git metadata is read-only;
no commit SHA exists yet. After the owner commits and pushes the explicit safe
files listed below, prepare one fresh clean detached six-mode acceptance at
that exact SHA. PR #18 remains draft. No Telegram, retained database, persistent
storage, deployment or merge was used.

## Attended adapter checkpoint

The PR now has a signed PTB update adapter, bounded one-off approvals and a separately owned worker in a disposable PG17 schema. Work ran 13 focused offline tests with zero skips, checked the shell runner syntax and verified six source digests. Native tests of the new schema, role locks and crash fencing await Acer. The existing synthetic and astronomy evidence retains its original scope. The recorded transport is the only runnable integration. Use the [single scoped Acer task](ATTENDED_CANDIDATE.md#disposable-adapter-acceptance). Gate 1 remains blocked.

## Accepted synthetic rehearsal and attended candidate

At `5bcda101bba4f10c1d87113da27e8f6ffc7b97b1`, Acer completed the native synthetic rehearsal with exit 0, all 15 checksums, signed relay and receipt checks, nine-table restore and unchanged inventory. The accepted four recurrence and nine historical tests carry forward. [Artifact decisions and attended candidate](ATTENDED_CANDIDATE.md) describe the offline preview renderer, remaining adapter work and separate owner gates. Earlier pending entries below document the historical sequence.

## PR 18 webhook registration race — focused fix, native validation pending

One browser-independent native rerun at `3409afad` reproduced forged-denial HTTP 404,
exit 1; cleanup/inventory passed. A separate disposable n8n-only diagnostic proved
activation may return 200/active before its webhook is registered; browser cookies are
not involved. Added a non-writing invalid-envelope readiness probe with bounded 404
retry and strict exact denial checks. Actual forged/foreign-owner and approval/lifecycle
assertions remain unchanged. No business SQL/workflow/staging-installer changes. Focused
offline tests and refreshed source checksums pass; no full native rerun after the fix.
Manual review resolved both unchanged scanner matches as pre-existing false positives
(SQL placeholder and synthetic password environment lookup); no scanner bypass or
weakening. Manifest checked with its designated checksum tool. Seven-file patch remains
uncommitted only because shared Git metadata is read-only.
See [rehearsal investigation](BETA_SCHEMA_REHEARSAL.md). Keep PR #18 draft; next native
acceptance requires a clean committed reviewed revision. No messaging or deployment.

## Personal schema rehearsal

[PR 18 rehearsal and consolidated Acer task](BETA_SCHEMA_REHEARSAL.md) records the new repository-owned synthetic schema, 19 offline tests and pending native gates. Review-only scope continues.

## Integrated personal beta cycle 1

[Implementation and Acer verification](BETA_CYCLE1.md) records 16 passing offline tests, source verification, the civil preview, isolated storage renderer, observer and encrypted synthetic archive. Personal schema adoption, image review and native journeys remain open before Gate 1.

## Current engineering checkpoint — offline beta runtime guard

New source-only development files:
[beta plan](beta-runtime-plan.json),
[preflight](../dincharya/beta_preflight.py),
[preflight tests](../tests/test_beta_preflight.py), and
[consolidated verification task](BETA_IMPLEMENTATION_CHECKPOINT.md).
All five conceptual runtime services, WhatsApp and Telegram egress,
startup, and promotion are disabled by default. The database is an
uncreated, isolated prospective personal-beta name; all image digests
remain pending. Nothing has been deployed or activated.

The new tests and previous source-pin tests require a clean Python-only
execution by Acer Codex; **no new test PASS is claimed yet**. Native
runtime, owner source adoption, independent alerting, encrypted routine
backup/restore and live-message owner approval remain future gates.
Do not reuse prior synthetic databases, change the synthetic-only
migration 0015 guard or start the existing mutable-tag Compose.


## Integrated Personal Beta — first implementation checkpoint (22 November 2026)

Source-review groundwork is committed on the development branch:

- [Pinned inventory](BETA_RUNTIME_SOURCE_INVENTORY.md): exact reviewed
  gateway, n8n, PostgreSQL 0015, reminder and staging artifact blobs at
  reference `894f32392185c26e7a59c390d337a62b564b9b8c`.
- [Inert manifest](beta-source-pins.json): 16 explicit reviewed file blobs,
  with `launch_authorized=false`, `telegram_egress_authorized=false`,
  `whatsapp_enabled=false`.
- [Offline verifier](../scripts/check-beta-source-pins.py) rejects changed
  files, duplicate/traversal/symlink paths and non-inert manifest flags.
  Five [focused regression cases](../tests/test_beta_source_pins.py)
  were added. **These tests have not yet been executed in Acer WSL**; run
  `python3 -B -m unittest discover -s tests -p test_beta_source_pins.py -v`
  and `python3 -B scripts/check-beta-source-pins.py` from a clean checkout
  before using this as acceptance evidence.

The current existing Compose file is **not** the approved personal-beta
launcher; migration 0015 is synthetic-DB guarded and must not be adapted to
a real persistent database by simply removing safeguards. Next development
task is a fresh disabled-by-default beta configuration and source-disposition
review, then a single consolidated isolated Acer Codex acceptance.
Do not touch prior tests/volumes, use private credentials, enable real
Telegram, start services or infer deployment authority from the manifest.


## Active owner decision — Integrated Personal Beta (22 November 2026)

The owner combined former Stage A (usable attended beta) and Stage B
(reliable operation) into one **Integrated Personal Beta** workstream with
**separate attended and unattended acceptance gates**. Implement both sets
of capabilities in one cohesive development candidate where feasible; do
not claim unattended readiness until independent monitoring/alerts, encrypted
off-device routine backup and verified restoration, single-host fencing and
separate owner authorization are complete.

**Telegram is the sole active messaging interface.** A conceptual future
WhatsApp transport adapter may be designed, but must not be implemented or
activated until separate eligibility/policy, business onboarding, template
constraints and cost review. No unofficial WhatsApp automation.

Use [the new implementation plan](INTEGRATED_PERSONAL_BETA.md) and the
[roadmap](ROADMAP.md) as the current work queue. Complete M2B revision-pinned
artifact disposition before beta source promotion; no fresh live messages,
credentials, ongoing personal scheduling, startup automation, production,
VPS or `main` merge is authorized by this planning decision. All prior
Stage 1/2 and PR #17 evidence remains preserved.


## Current checkpoint — development PR consolidation complete (22 November 2026)

PR #17 merged into the development branch by merge commit
`62421931de6dad60d389c7d8951cecf2fef1b68e` (first parent
`7fc20d6c05e037b0ac3f01d11c5868b715476bd3`; second parent
`4674c5d9ea3751272b8b1492849a324b2479f738`).
On Acer WSL, both gateway preflights passed without skips and the fresh,
networkless PostgreSQL 17 migration 0015 receipt gate passed (exit 0);
disposable cleanup preserved prior environments.

All original historical PR heads were independently verified as ancestors
of that integrated development history. PR #4 was automatically marked
merged; #5 and #7–#16 were subsequently closed **as superseded**, not merged
individually. Their remote branches, histories and comments are retained.

Next: artifact-level Milestone 2B owner dispositions and a new, explicitly
approved attended personal-beta scope. The prior Telegram acceptance was
one-use. No authoritative source promotion, persistent personal scheduling,
unattended operation, production, VPS deployment or `main` merge is authorized.
Preserve the Stage 1/2 evidence, aborted recovery, observer-tail qualification,
owner-accepted USB warning and deferred SMB.


The [consolidated integration review](PR_STACK_INTEGRATION_REVIEW.md) records all twelve PRs, receipt-safety migration 0015 and one fresh PG17 validation gate before the proposed development-only merge. Attended Telegram use requires a separate scoped approval.

## Final scoped cleanup complete

Acer cleanup was verified locally: original SSH service restored Manual/Stopped;
temporary monitoring account/two rules removed; no test listener and unrelated rule
inventory unchanged. Owner-returned ThinkPad cleanup confirms the saved-SID receiver
account, exact share and two backup rules removed, original directory permissions
restored and unrelated rules unchanged. All databases, journals, evidence, keys,
encrypted archives and restore records retained; retired monitoring configuration is
inactive evidence. No Docker/WSL uninstall, power change or automatic startup.

Stage 2's approved recovery-only acceptance and scoped cleanup are complete with the
observer-tail limitation and owner-accepted USB filesystem warning retained. SMB
transport remains NOT TESTED / DEFERRED, replaced by verified USB transfer. No repeat
physical test is required by this closeout. PR #16 remains draft; GitHub currently
reports it not mergeable, so stack/base review is needed before any merge approval.
Next: commit the explicit closeout docs, review the PR stack and approve a bounded
attended personal beta at a named revision. Manual startup only; no live scheduling,
Telegram or deployment is enabled. Unattended beta needs separately approved independent
monitoring/alerts and scheduled backup/recovery. Broader Milestone 2/source/calendar
release gates are not closed by this acceptance. See [results](LAPTOP_STAGE2_RESULTS.md).

## Recovery-only acceptance passed — documented limitations retained

At `b89a2bc`, recovery-only functional checks and 435.014-second startup passed: four
paired receipts, zero silent/duplicate attempts, one quarantined uncertain without
resend, durable history and single-worker enforcement. CMS export/source task exit 0.
Owner-returned ThinkPad execution verified USB/destination hashes and independent
networkless PG17 restore: exit 0, migrations plus all six histories equal, 5 slots/4
sent/1 uncertain, no app/worker. Final Acer inventory comparison passed; prior Stage 1
projects and aborted physical session remain unchanged. No repeated lid test.

Limitations retained: observer trace passed outage/recovery criteria but ends before
final fixtures; later outcomes were verified by SQL/recorder/restart, not external
monitoring. Possible ThinkPad Docker crash is unconfirmed. Owner explicitly accepted
USB volume Warning/Full Repair Needed; filesystem health is not passed. SMB testing
remains deferred. See [complete evidence](LAPTOP_STAGE2_RESULTS.md).

All source application services and the attended Acer bridge/Stage 2 SSH listener are
stopped. Backups/logs/journals retained. Acer monitoring cleanup is verified: original SSH service restored Manual/Stopped,
temporary monitor account/two firewall rules removed, unrelated rule inventory unchanged.
ThinkPad receiver cleanup is now owner-confirmed complete; see final checkpoint above.
Commit the explicit four closeout documents listed in the final report to the existing PR branch.
No further arming, reboot, resend, production, permanent deployment or merge authorized.


## Historical Stage 2 checkpoint — aborted after missed recovery window

The 22 November attended run at approved `fb023f1` passed initial arm/open and two paired receipts, then stopped for the supervised reboot. The bounded recovery guard rejected timing; no recovery phase was reserved. Documented abort/stop exited 0 and prior Stage 1 inventories remained unchanged. Final counts, observer continuity, USB export and independent restore are not accepted. Preserve all state; do not replay phases. See [actual results](LAPTOP_STAGE2_RESULTS.md). Another physical attempt/reboot needs fresh authorization. Temporary monitoring/SMB cleanup and collection of the complete ThinkPad observer log remain pending.

The original [Stage 2 task](LAPTOP_STAGE2_PHYSICAL.md) and approved recovery-only continuation are recorded separately in the results. Original aborted phases must never be replayed.

## Latest WSL checkpoint — combined Stage 1 passed

The [combined Stage 1 acceptance](LAPTOP_STAGE1_COMPLETE.md#verified-wsl-run--19-november-2026)
executed once at approved `da6d08e2b583266af7615f9a5b86de9f6bd66131` on
`development/stage1-confirmation-recheck`. **All six checks passed: journey 0,
stop 0, overall script 0.** Existing verified runtime/kernel, pinned daemon and
accepted images were reused. No previously accepted suite was repeated.

Actual timed evidence: four approved schedules/controls/audits; three slots;
zero legacy delivery rows; two paired accepted receipts; one uncertain attempt
with no receipt or replay; zero silent attempts. Competing worker exited 75.
Controlled outage/recovery retained recorder and SQL history, caught up once,
rejected a stale review and exposed the expected quarantine health. Quiesced
local CMS-encrypted synthetic dump restored networklessly with checksums and
all six tracked histories equal (3 slots, 2 sent, 1 uncertain).

All five complete-project services exited 0; its four volumes and stopped
containers are preserved. Both earlier projects' exact stopped states and volumes
and unrelated inventories are unchanged. No historical approval was replayed,
no source correction was required, and the original Stage 1 failure is not
retroactively erased or explained. No real Telegram, private baseline, Windows
change/reboot/task registration, deployment, promotion or merge. Physical and
off-host acceptance remain separate gates. Preserve all three stopped projects
until their disposable cleanup scope is reviewed.

Only this handoff and the combined acceptance report changed after stopping.
Git metadata remains read-only. Normal WSL safe-file commands:

```bash
git branch --show-current
git diff --check
git add -- docs/HANDOFF.md docs/LAPTOP_STAGE1_COMPLETE.md
git diff --cached --check
git diff --cached
git commit -m "docs: record successful combined Stage 1 WSL acceptance"
git push origin development/stage1-confirmation-recheck
```

The earlier targeted confirmation recheck and Work's eleven focused staging
tests remain accepted at their original scope; neither was rerun here.

## Latest checkpoint — PR #15 targeted WSL recheck passed

The [single fresh confirmation recheck](LAPTOP_STAGE1_RECHECK.md#verified-targeted-wsl-re-acceptance)
passed at approved `7ec5d0b5fc969e9f4dc275b661b5c891453deacf` on
`development/stage1-confirmation-recheck`: **journey exit 0; stop exit 0**.
Three focused confirmation tests passed. The real offline SDK, signed native
n8n relay and PostgreSQL independently agreed on the first confirmation and,
only afterward, the duplicate callback. Both produced one approved reply,
no fallback, no keyboard and a true committed-control match. Persistence stayed
at one event/control/audit with zero slots, legacy deliveries, delivery attempts
or recorder attempts. No first mismatch or source correction.

The original Stage 1 failure was not reproduced or explained. Its five stopped
containers, four volumes and container state remain unchanged. The separate
recheck's five containers all stopped with exit 0 and its four volumes are
preserved. Unrelated container/volume inventories and accepted base image are
unchanged. No original approval was replayed. Do not reuse or clean either
project without reviewed scope. Broader timed-delivery/restart/quarantine and
physical acceptance remain pending. No real Telegram or production operations.

Only this handoff and the recheck evidence changed after stopping. Git metadata
is read-only; reviewed safe-file commands for normal WSL:

```bash
git branch --show-current
git diff --check
git add -- docs/HANDOFF.md docs/LAPTOP_STAGE1_RECHECK.md
git diff --cached --check
git diff --cached
git commit -m "docs: record passing targeted Stage 1 confirmation recheck"
git push origin development/stage1-confirmation-recheck
```

Stage 1 originally stopped after the silent approval committed and its response
check failed. Preserve that original evidence and project separately.

## Latest WSL checkpoint — laptop Stage 1 partially passed

[Verified Stage 1 results](LAPTOP_STAGE1_RESULTS.md) record the exact approved
`37db544a872676ae75e2cacfa32b92f5775f2d46` on the owner's PR-head branch alias.
The owner separately approved official Python 3.12 base selection. Its immutable
linux/amd64 digest, Python 3.12.16, libraries, timezone and build evidence are in
the report. The image, invented schema and five-service isolated startup passed.

The synthetic gateway approval-response assertion failed after one silent event,
one recurring control and one audit record persisted; zero slots/attempts were
observed. No reminder/receipt, runtime quarantine, concurrent-worker or restart
acceptance is claimed. Five focused repository tests and the networkless SDK
response reproduction passed independently. The failure cause is not yet
established; the report proposes bounded diagnostics for review, not a speculative
application fix. Approved application source and migrations are unchanged.

All five staging containers stopped with exit 0. Four staging volumes and stopped
containers are preserved; unrelated inventories are unchanged. Do not reuse or
delete the partially initialized project without reviewed cleanup scope. No private
baseline, real bot, Windows changes, reboot, persistent installation or deployment.
Physical and off-host restore acceptance remains untested. Earlier Cycle 7
acceptance is preserved separately.

Only documentation changes follow the run. Git metadata remains read-only.
Normal WSL, review and commit these exact safe files on the current PR branch:

```bash
git branch --show-current
git diff --check
git add -- docs/HANDOFF.md docs/LAPTOP_STAGING.md docs/LAPTOP_STAGE1_RESULTS.md
git diff --cached --check
git diff --cached
git commit -m "docs: record partial laptop Stage 1 acceptance and verified base"
```

The local branch is `development/pr14-laptop-staging`; PR #14's remote head is
`development/laptop-staging-infrastructure`. After reviewing the documentation
commit, publish without force:

```bash
git push origin HEAD:development/laptop-staging-infrastructure
```


The [laptop staging implementation and consolidated WSL task](LAPTOP_STAGING.md) cover synthetic startup, supervision, recovery and cold transfer. Five focused checks passed in Work. Full Compose and physical acceptance remain pending.

Prioritize the [laptop-hosted personal beta](LAPTOP_BETA.md) before India VPS handover. Physical lid, reboot and host-fencing acceptance remain pending.

Read root [AGENTS.md](../AGENTS.md), [policy](DEVELOPMENT_POLICY.md),
[roadmap](ROADMAP.md), [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md).

## Current checkpoint — Cycle 7 final acceptance handoff

The owner-authorized private test on 18 November 2026, 12:15–12:26 IST,
**PASSED, exit 0**, using the exact approved revision
`72286479d8b52aa0e5b34c3c2db19f14883281eb`. Both explicit appointment approvals
completed before the deadline. Six chat attempts and six acknowledgements;
one real reminder attempt and one paired database receipt; zero silent sends
and no duplicates through the final two worker checks. Owner confirmed the same
counts on their device. Original schema bytes unchanged, disposable teardown
verified and unrelated running-container IDs unchanged. No application correction,
retry, resend or history reset was required. See the
[completed private evidence](M2H_CYCLE7_PRIVATE_ACCEPTANCE.md#completed-authorized-private-session--18-november-2026).

This one-use authority is consumed. Preserve the reservation and keep the
protected approval and credential outside Git under owner custody. No more
Telegram operations, production promotion, deployment, merge or general lunar
scheduling is authorized. Sanitized results are recorded in issue #6.

Only this handoff and the private acceptance report changed after the run.
Git metadata remains read-only; normal WSL commit commands:

```bash
git branch --show-current
git diff --check
git add -- docs/HANDOFF.md docs/M2H_CYCLE7_PRIVATE_ACCEPTANCE.md
git diff --cached --check
git diff --cached
git commit -m "docs: record bounded Cycle 7 private Telegram acceptance"
git push origin development/m2h-private-telegram-acceptance
```


[Cycle 7 WSL acceptance](https://github.com/vasu1765/dincharya-ai/issues/6#issuecomment-6970326525) passed with exit 0 at the verified PR #11
revision. Its exact-schema check used the same disposable database. The
[cross-cluster synthetic rehearsal](M2H_CYCLE7_RELEASE.md#end-to-end-acceptance-matrix)
provides separate recovery evidence. Use the
[private Telegram runbook](M2H_CYCLE7_PRIVATE_ACCEPTANCE.md) after revision-bound
owner authorization. The [source decisions](M2B_CYCLE7_DECISIONS.md) remain for
review before any promotion.

## Prior checkpoint — M2H Cycle 7 release readiness

The [end-to-end matrix and release checklist](M2H_CYCLE7_RELEASE.md) document
synthetic acceptance and the restore fence. The prior exact Cycle 6 result and the later 0014 compatibility result are preserved.
[Source dispositions](M2B_CYCLE7_DECISIONS.md) and
[private test scope](M2H_CYCLE7_PRIVATE_ACCEPTANCE.md) are ready for separate review.

## Prior checkpoint — M2H Cycle 6 historical Panchang and source review

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
