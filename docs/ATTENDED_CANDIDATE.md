# Attended personal beta candidate

## Final attended runtime candidate

Acer's corrected working-tree journey exited 0 with six paired receipts, one reminder, rejection after approval consumption and unchanged inventory. That run staged the legacy astronomy wheel on the fixture's main import path. The first clean committed run of the isolated runtime is pending.

The operator uses the application image's certifi 2026.10.23 PEM. It verifies the bytes against the SHA-256 in that immutable distribution's RECORD and loads them explicitly into a hostname-verifying client TLS context with TLS 1.2 minimum. Acer prints the measured CA SHA-256 before the recorded journey. The legacy wheel enters only a short-lived Python child started with isolated and no-site flags, a scrubbed environment and closed inherited descriptors. This is dependency isolation within the reviewed app container. The unchanged astronomy calculator still verifies its dependencies, reference files and ephemeris.

| Runtime input | Approved local content identity |
| --- | --- |
| Linux/amd64 PG17 | sha256:ff87138949ad9a46f32ff23bd6852b52ce024a13dffe9b4087be98292cdd3b4f |
| Application, including Telegram TLS trust | sha256:fff0b1b58321339ad0de04804548cb8ff14c9a929e6eead08ce3cd96535493ca |
| Native n8n | sha256:6723b440354bb8e1395a1ecee12685fe03923f897bf6e4d5bb2c6c2bd2051697 |
| Public certifi 2025.10.5 wheel, astronomy child | 0f212c2744a9bb6de0c56639a6f68afe01ecd92d91f14ae897c4fe7bbeeef0de |
| Public DE440s kernel | c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2 |

Use these existing images with pull disabled. Place the verified wheel beside de440s.bsp in the read-only /run/attended mount, with its original filename. Keep the operator root filesystem read-only, the image environment intact except PYTHONPATH=/candidate, and the committed Git archive read-only. The host check verifies the three image identities and the private/egress network split. The external Telegram-only outbound firewall rule and old-host fencing require independent host evidence. Mount paths and firewall rules remain frozen for the session.

### One disposable Acer command

Use a fresh clean detached checkout at the exact PR handoff SHA. Export REV to that SHA and KERNEL and CERTIFI_WHEEL to the already reviewed public files. From the checkout root run:

```bash
set -eu
test "$(git rev-parse HEAD)" = "$REV"
test -z "$(git status --porcelain)"
sha256sum -c docs/attended-operator.sha256
read -r PG APP N8N < <(python3 -B -c 'from dincharya.attended_runtime import PG,APP,N8N;print(PG,APP,N8N)')
export PG APP N8N
bash tests/integration/operator_path.sh
```

Use Bash. This invokes the real CLI with disposable mounted inputs and recorded Telegram HTTP; the relay, database and child historical calculation run natively. The fixture also checks valid private-fixture TLS, rejection of an untrusted issuer and rejection of a wrong hostname. Report measured CA hash, six ordered receipts, consumed-manifest restart rejection, exit and cleanup/inventory. Preserve the first failing stage. End after this one run.

### Single-session owner authorization template

Fill every bracket after acceptance. Record non-public identity fields privately. The operator derives chat and recipient from the same private owner ID.

> I authorize one manually attended disposable session at [exact accepted SHA], manifest SHA-256 [digest], on Acer daemon 44c1ef83-c50e-4ecc-8f19-4b112bc40f29. I approve the three image IDs, DE440s and child-wheel digests in this revision and measured Telegram CA SHA-256 [digest]. Dedicated bot dincharya_acceptance_test_bot has numeric ID [bot]. The sole owner, private chat and recipient are [owner]. The fresh tmpfs database dincharya_attended_test is [container ID]. The poller and worker are fenced to [host], with verified Telegram-only egress. From [absolute IST start] through [absolute IST end], allow [exact historical question], [exact silent Schedule command and IST time] and [exact at-start Schedule command and distinct IST time]. I will confirm each preview separately. Permit at most six outbound chat attempts including one reminder on success. Stop on cancellation, deadline, budget, identity, network or receipt mismatch, lock loss or uncertainty. Fence the host, disable the database session and preserve receipts. No automatic resend or restart.

Manifest times are Unix seconds and the maximum window is one hour. Keep credentials outside Git and PR evidence. Privately verify the filled manifest against the host preflight, including the exact UTC-to-IST conversion. A pending run, an unverified egress rule or an unfilled field keeps live execution blocked.

## Earlier operator acceptance evidence

The six adapter scenarios at `86d4a69b77c6c429a9408658243ff9de3d28209c` passed on Acer, including cleanup and unchanged Docker inventory. The transcript did not print a separate numeric final exit status. Keep the earlier PostgreSQL, astronomy and physical evidence at their accepted revisions.

The operator holds both role connections for its lifetime, consumes a separately provisioned one-use approval and verifies the dedicated bot before polling. It calls getUpdates explicitly, one update at a time. Only sendMessage transmits chat content. Bot API HTTP requests disable retries, redirects and environment proxies. There is no webhook deletion, callback answer, startup greeting or error reply. Each signed update must return through the native relay with matching payload and signature before dispatch. All outgoing messages, including the read-only historical answer, use the same PG17 reservation and paired-receipt functions. The operator exits after six attempts, cancellation, a deadline, a stop signal or an unexpected result. A consumed approval cannot resume.

### Prior fixture procedure (superseded)

In a clean detached checkout of the exact operator SHA recorded on PR #18, export REV, the accepted full local image IDs PG, APP and N8N, and KERNEL pointing to the previously reviewed public de440s.bsp. Set CERTIFI_WHEEL
to the absolute path of the public `certifi-2025.10.5-py3-none-any.whl` recorded
in `prototypes/panchang/ephemeris.json`. The disposable runner verifies the
staged wheel bytes against that lock before starting a container. The pinned
application image supplies certifi 2026.10.23, so the fixture puts the verified
wheel first on the recorded operator's Python import path. The live launcher
does not use this fixture overlay. Run:

```bash
set -eu
test "$(git rev-parse HEAD)" = "$REV"
test -z "$(git status --porcelain)"
sha256sum -c docs/attended-operator.sha256
bash tests/integration/operator_path.sh
```

The runner uses one fresh internal network, an ephemeral PG17 database, native n8n and recorded Telegram HTTP. It executes one historical lookup through the unchanged calculator. Expected evidence is a consumed approval, rejection of a second startup and six positive receipt pairs in order: historical, preview, decision, preview, decision, reminder. Record the image IDs, revision, each stage, exit and cleanup/inventory outcome. Stop on missing image dependencies or any mismatch. Keep the first failure stage and avoid replaying the session.

### Live manifest and manually attended procedure

After disposable acceptance, obtain explicit owner approval for the exact executable SHA, full PG/APP/N8N image IDs, public kernel SHA-256, Docker daemon ID as host fence, numeric bot ID and username dincharya_acceptance_test_bot, private owner ID equal to chat and recipient, exact historical question, both exact appointment commands and absolute IST window (maximum one hour). The silent and reminder fields use `Schedule TITLE on YYYY-MM-DD at HH:MM`; the owner appends `; at start` to the reminder request in Telegram. Confirm each preview separately. Limit the session to six attempted outbound chat messages, including exactly one genuine reminder on successful completion.

The JSON manifest has exactly the fields of the frozen Approval object: sha, host, pg, app, n8n, bot, owner, start, end, silent, reminder, question, kernel_sha256. Start/end are whole Unix seconds. Approve the SHA-256 of the exact manifest bytes separately. On a fenced host provision a fresh tmpfs database, apply only attended/0001 and 0002, provision the scoped logins and insert the exact identities and timestamps in attended.session. The administrator inserts the approved digest into attended.operator_approval with consumed=false. Enable the session only within the separately approved procedure.

Stage a fresh private relay using the reviewed workflow, with no saved execution data, telemetry or public listener. Its request target must be http://app:8080/lunar. Isolate PG and n8n on the private network. Enforce the host egress policy so only the application can reach the Telegram Bot API. Mount a reviewed Git archive of dincharya and prototypes/panchang read-only at /candidate, with PYTHONPATH and working directory /candidate. The dedicated app container hostname equals the approved daemon ID. Its read-only /run/attended mount holds manifest.json, revision, public de440s.bsp and the separately provisioned bot.key, relay.key, poller.key and worker.key. Restrict mount access to the attended identities. Keep the mount under operator control so adding STOP takes effect immediately before the next operation.

Prepare the stopped app with entrypoint python and arguments `-B -m dincharya.attended_operator --attended --approval DIGEST`. Verify the exact three container IDs, network memberships, host fencing and stop control. Run `PYTHONPATH=. python scripts/attended_operator_host.py MANIFEST DIGEST PG_CONTAINER APP_CONTAINER N8N_CONTAINER` on the host. Preserve the approved mounts and network configuration unchanged between preflight and manual startup. Default invocation without --attended exits before reading credentials.

On any mismatch, owner cancellation, uncertain acknowledgement, unexpected egress, lock loss or deadline, create STOP, disable attended.session, stop polling and delivery and fence the host. Preserve the attempt ledger and paired receipts. Inspect unresolved reservations without resending. A fresh session requires separate owner approval. Restrict summaries to counts, stage and disposition. Keep credentials, chat contents and personal IDs out of PR evidence.

## Disposable adapter acceptance

The source candidate binds recorded python-telegram-bot updates to the signed handler and the existing one-off preview. An administrator provisions the synthetic owner, bot and short window only in a fresh disposable PG17 database. Separate session logins hold poller and worker locks. The signed callback must present a canonical proposal UUID, matching preview receipt, private owner and originating bot. A proposal becomes scheduled only on confirmation. An unanswered preview expires after at most 15 minutes.

All roles share six durable outbound reservations. A second database statement consumes a single-use transport permit after checking the window and destination. A valid response pairs the owner chat and positive message ID and identifies the pinned bot. Missing acknowledgements fence both roles. A successor quarantines abandoned reservations for its role. Stop both processes on any unexpected outcome, disable the session, and retain the attempt history. Do not reuse a restored copy to resume outbound work. This candidate offers no operator interface for clearing quarantine. The operator reconciliation review for the existing rehearsal schema remains separate.

**One Acer WSL task.** Use a new clean detached worktree at the exact SHA in the PR handoff. Export that SHA as REV and reuse the previously verified full local PG and APP image IDs from Acer acceptance. The runner requires the accepted Docker daemon, uses fresh internal-only resources, records Telegram I/O in process and checks inventory after cleanup. Run from the repository root:

```bash
set -eu
test "$(git rev-parse HEAD)" = "$REV"
test -z "$(git status --porcelain)"
sha256sum -c docs/attended-delta.sha256
bash tests/integration/attended_delta.sh
```

Report exit code, each scenario and cleanup/inventory status. Expected successful appointment evidence is two confirmed appointments, five reservations with paired receipts and exactly one reminder. Other independent fixture cases cover six attempts across restart and rejection of the seventh, uncertain delivery, abandoned reservations, disabled sessions and an expired proposal. Preserve the failed stage on interruption and do not replay its approvals. Work verified 13 focused offline tests and six file hashes. Acer evidence for these changes is pending.

### PR #18 appointments diagnosis and focused correction

At the original candidate SHA `c8b981d46d7933c042a8bd77a40d049f7c6ed730`, the full native task stopped at `appointments_journey` (exit 1) and cleaned its disposable resources. The three callback-negative checks are valid: they alter the preview origin ID, callback token, and preview message's bot identity. All three passed in the focused run; those identities and authorization checks are unchanged.

A fresh focused PG17 run reproduced the failure at the final delivery assertion: four owner-visible messages existed and the worker had created no reminder attempt. Aggregate SQL evidence showed one confirmed reminder appointment that was still two seconds in the future according to PostgreSQL when the application-clock wait had ended. The worker correctly produced no reminder attempt. The test now waits against `clock_timestamp()` on its scoped worker connection, with a bounded timeout and a 55-second maximum lateness inside the SQL worker's one-minute eligibility grace. It does not retry transport or alter the due predicate.

The integration harness emits fixed substage labels and sanitized exception class/SQLSTATE; it suppresses exception text, payloads, credentials and signatures. The fixture records only a count and boolean for the final reminder assertion. Shell cleanup surfaces only the fixed diagnostic forms. SQL privileges, advisory locks, callback origin/bot/owner checks, appointment window checks, reservation-before-send, and paired receipt settlement remain unchanged.

Focused verification on the corrected working tree: four database-clock timing unit tests, eleven gateway tests and two attended preview tests passed; syntax and shell checks passed. One appointments-only disposable run passed role-lock exclusivity, duplicate updates, forged origin/token/sender rejection, separate approvals across poller restart, worker restart, and duplicate tick suppression. Its final evidence was five attempts/five paired sends, one reminder, two confirmed appointments, zero uncertain deliveries; cleanup and full container/network/volume/image inventory comparison passed. The other five native modes have not yet run against this correction. This is focused evidence only, not full native acceptance or the live gate.

**Live gate.** After native acceptance, review and pin the actual operator entry point for polling, SDK transport timeouts/retry suppression, signed relay routing, stop controls and the historical reply sharing this budget. These are outside the recorded adapter's execution path. Require fresh approval for the exact runnable SHA and source/image digests, dedicated bot ID and username, private owner/chat/recipient ID, manually fenced host, absolute IST window and both civil event times. Count every outbound chat attempt, including ambiguous ones. Permit one historical answer, two previews, two confirmation replies and exactly one reminder. Stop on the first unexpected recipient, identity, window, ownership, budget, receipt, egress or health result. Preserve evidence and close the disposable session.

## Decision and evidence

The coordinator accepted one synthetic run at `5bcda101bba4f10c1d87113da27e8f6ffc7b97b1`: native exit 0, 15/15 checksums, signed n8n and owner decisions, paired receipt, quarantine, scoped operator reconciliation, restore comparison of nine tables on a second container on the same daemon, and unchanged Docker inventory. Four recurrence and nine historical regressions carry forward. This review recommends source reuse only. Personal database creation and source promotion require explicit approval.

## Artifact decisions

The first 15 entries are SHA-256 at the accepted revision. The remaining 16 are the Git blob identifiers in the original source inventory. “Adopt” means recommend the reviewed contract for development. No artifact has been promoted by this review.

| Repository artifact | Content identifier | Recommendation | Boundary or required verification |
| --- | --- | --- | --- |
| `database/personal_beta/0001_civil.sql` | `6ccfe7b51475545511750c4551aea360d1472e5d47de98f2caba690654639a75` | Adapt | Separate personal migration and clean volume. Replace fixture 101 with provisioned identity consistently in drafts, receipt constraints, claims and permits. Verify revoked access, conflict rollback and stale epochs. |
| `dincharya/recurring_intent.py` | `73b661c0af46b2d0c7599a72546eaf0410330df417994f356715399e97c9a4a8` | Adopt | Reuse deterministic civil parsing. Restrict the first window to one-off activities at preview and commit. |
| `dincharya/beta_preview.py` | `53b7373efa9ae8d05bc047bce71ed9e655147acc0f6016aed228578e3762b13c` | Adapt | Bind chat and sender to attested login identity. |
| `dincharya/beta_dispatch.py` | `a5d0c5ddcc989b23afd7c3494be6aafd768670e0c59680e1f3ee845dc0cf4b4a` | Adapt | Preserve HMAC and replay binding. Replace rehearsal-only DB and owner checks with separately reviewed personal identity checks. |
| `dincharya/beta_observer.py` | `e0f239362041f0e013d9cb49908ef584daf03b220e015d213745b71e1292fb6a` | Defer | Transitions tested; independent host and owner alert proof belongs to unattended acceptance. |
| `dincharya/beta_archive.py` | `376553457d143a73b6c85d2075f1fa9bfd94ab4d5c45500fe053ce0f518bb52a` | Adapt | Require completed dump, approved recipient and authenticated decrypt before restore. Independent media acceptance outstanding. |
| `tests/test_beta_review.py` | `ec9c62ab5cb787fa123236e4ffef764fed3717773e5b49197f66328b7e11e6b4` | Adopt for rehearsal | Preserve as test evidence only. Rerun only affected assertions. |
| `tests/test_beta_cycle1.py` | `6ec9f392b9a9b963794ffb36fd82a89bec8c3ba8047d1a7a44a5450e4337a33b` | Adopt for rehearsal | Preserve as test evidence only. Rerun only affected assertions. |
| `tests/integration/beta_native.sh` | `e32507a682df75a67d643f025ead92d81ee8a725963475ef888e9f3dd8b06dfe` | Adopt for rehearsal | Preserve as test evidence only. Rerun only affected assertions. |
| `tests/integration/beta_native.sql` | `cc1bbba9fe37e5f2c0cd709e78d2f0c61801a3efea241a254b1adfc043aa4860` | Adopt for rehearsal | Preserve as test evidence only. Rerun only affected assertions. |
| `tests/integration/beta_relay_journey.py` | `84e3a7d467ae09bc31a05c561e3a4705ce53f3097eb292c8ad5a8cfa023d09d9` | Adopt for rehearsal | Preserve as test evidence only. Rerun only affected assertions. |
| `tests/integration/beta_focused.py` | `a47d97879f80f3cc07af9add1d7cb35a2456b8df6e3e836218c0a6022ba75ef3` | Adopt for rehearsal | Preserve as test evidence only. Rerun only affected assertions. |
| `tests/test_beta_native_diagnostics.py` | `3323276f9414b7d85f5f0e702d42680e1b6800a82b019eef7573ff11c10de639` | Adopt for rehearsal | Preserve as test evidence only. Rerun only affected assertions. |
| `tests/test_beta_resolution_schema.py` | `bb2f86a1e83968851511d9d6e9f4deab70969046cb2995be2fbec5981e4ad971` | Adopt for rehearsal | Preserve as test evidence only. Rerun only affected assertions. |
| `tests/test_beta_relay_diagnostics.py` | `20327097a7e429992cef5bba8bb525be0338d55711f08a4988c8791be01f50ba` | Adopt for rehearsal | Preserve as test evidence only. Rerun only affected assertions. |
| `telegram-gateway/gateway.py` | `a90b0ab133fc687204c63063788bc698d64e8103` | Adapt | Register only permitted handlers after bot identity and exclusive polling lock verification. |
| `telegram-gateway/lunar_handlers.py` | `5bdb78b57f1d69868eb257afcc09ac9de14c3b66` | Adapt | Reuse signed relay transport; omit annual and festival writes. |
| `telegram-gateway/reminder_handlers.py` | `a8a2b6a2b8710b1de03382ddbbdc65076e0352f5` | Adapt | Disable embedded worker when separate worker owns delivery. |
| `telegram-gateway/lunar_acceptance.py` | `00e0e5f2e8fd6258dbe50f860f2ef28a3d2a1618` | Defer | Dedicated rehearsal entry point; no general polling authorization. |
| `telegram-gateway/requirements-m2g.txt` | `bde0c5278ba5096c5808436d979d6773c05bfe9f` | Adapt | Resolve reviewed wheel hashes and exact immutable application image. |
| `dincharya/reminders.py` | `515e628d706ab1b330e6ecc23ea975e6de6701ee` | Adopt | Reuse single-batch processing and uncertain-outcome quarantine. |
| `dincharya/reminder_adapters.py` | `e5ed9c25f049ac6a5e95c11c187a81782202d6e8` | Adapt | Bind restricted personal slots and destination; test lost acknowledgement with no resend. |
| `dincharya/lunar_runtime.py` | `4d4d2238230409a0dd8a1c68a83653440ad378ef` | Defer | Retain synthetic DB and live-approval guards. |
| `dincharya/lunar_service.py` | `8ed7b11bef76b904ca0ecf81c3c7528ea5d6ae30` | Adapt | Reuse signed envelope; exclude fixture connection and catalog. |
| `database/migrations/0015_managed_receipt_safety.sql` | `dd4d76d4855f08c79c224128979d44efb57ee100` | Defer | Historical 0001–0015 chain and guards stay frozen; paired receipts are mandatory in the new chain. |
| `workflows/m2g-lunar-acceptance.json` | `f79027b0e8534a2978ffb4080e87d2569ed57873` | Adapt | Pin inactive workflow and reviewed n8n image; verify readiness before dispatch. |
| `tests/integration/receipt_candidate.sh` | `2042d153481878543cd03b945eb48da59df51132` | Adopt for rehearsal | Preserve as test evidence only. Rerun only affected assertions. |
| `tests/integration/compose.json` | `1ae4134386b86ac1e03bfc86dcbff4b355d7284e` | Adopt for rehearsal | Preserve as test evidence only. Rerun only affected assertions. |
| `staging/laptop/service.py` | `3d871f3a39dae746d622915cfd9a62f59cffba95` | Defer | No synthetic recorder or fixture administration in attended runtime. |
| `compose.yaml` | `e76126cdbb98718e4ad194147acd6fd4ad08bc5e` | Defer | Mutable images and existing storage are outside the beta. |
| `docs/m2b-repository-review.json` | `b51199505cb3a2f231b4e6e494fcf5bd3bffae81` | Adopt for review | Keep provenance ledger; exclude historical/private inputs. |

## Manual attended path

The existing preparation plan keeps startup, all services and messaging disabled. The new offline appointment renderer consumes the accepted dispatcher preview, displays the exact civil date, local time and notification policy, and returns Confirm/Cancel buttons tied to the proposal UUID. It has no credential, destination, polling, persistence or send interface. Only the separately authenticated dispatcher can decide the proposal.

Before integration, implement personal identity provisioning on a fresh disposable schema variant, scoped logins, a bot-origin check on callback messages, single active poller and worker, and an atomic attempt budget shared across service restarts. Use separate relay and worker authority. A transport receipt must pair the approved recipient and message ID. After loss of acknowledgement quarantine and stop. Reconciliation requires independently verified positive evidence and an unexpired operator permit; never turn a review into a resend.

## Previous renderer-only checkpoint (superseded)

At the pinned adapter revision, use fresh disposable storage, synthetic identities distinct from 101, pinned images, an isolated relay and recorded SDK I/O. Exercise only the changed binding and worker paths: mismatched bot/chat and stale callbacks rejected; silent appointment with zero slots; one confirmed at-start appointment with one paired receipt; repeated confirmation and second worker rejected or idempotent; process loss after send leaves quarantine; budget and stop survive restart. Verify no unexpected traffic and unchanged unrelated Docker inventory. Record exact pins, counts and exit on PR 18. There is no WSL task to execute for this renderer-only revision.

## Owner approval package for the first session

At the live gate, supply the reviewed executable SHA, schema and image digests, exact dedicated bot ID/username, private owner ID equal to recipient/chat ID, fresh disposable database, manually fenced host, and an absolute start/end IST window. Record the permitted activities and maximum six outbound chat messages: one read-only historical reply, two civil previews, two confirmation replies and one at-start reminder. The silent event produces zero reminders. Pick the two distinct event times inside the named window before approval. Count attempts before I/O, including uncertain sends. Require a new explicit confirmation for each schedule write. Automatic startup and general scheduling remain disabled.

Stop on an identity, approval, revision, budget or time mismatch, missed lease, uncertain send or unexpected egress. Stop polling and delivery, fence the host, preserve receipts and action history, and invalidate stale approvals before recovery. End the session at the cap or deadline. Persistent personal storage is a separate artifact decision; the first bounded session can use disposable storage. Unattended operation requires independent outage alert delivery, encrypted off-device restore on healthy media, host fencing and supervision, and separate owner approval.
