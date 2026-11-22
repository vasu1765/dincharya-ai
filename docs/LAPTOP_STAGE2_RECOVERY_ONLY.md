# Stage 2 accelerated continuation — owner approved; runtime pending

This amendment preserves the aborted 22 November run at application revision
`fb023f11244a6b116c7ae1d17cb3b3c8cce9e6a7` and completes only its remaining gates.
The owner approved the revised isolated harness, criteria, one additional supervised
reboot and USB continuation in chat. Runtime remains gated on a reviewed clean
checkpoint, exact-target observer readiness and fresh owner attendance. No runtime
execution has occurred at this implementation checkpoint.
No repeat of Stage 1, SSH connection restrictions, infrastructure acceptance or the
30-minute physical lid interval is proposed.

## Preserved evidence and isolation

Retain the successful closed-lid checkpoint/open validation and two paired receipts
at their original scope. Do not relabel the original missed-window recovery as passed.
Collect and preserve the existing ThinkPad observer JSONL and actual close/open times;
complete log correlation remains pending documentary verification, not a new physical
exercise. Record any evidence gap explicitly. Preserve all existing acceptance reports.

The aborted project's containers remain stopped; its database, volumes, recorder and
journal remain untouched. No recovery, export, deletion, renamed state or phase-marker
reset in that project. Read-only inventory/state fingerprints are taken before/after
continuation. All three Stage 1 environments remain unchanged.

Use a new exact allowlisted project/state namespace `dincharya-stage2-recovery-only`,
with fresh synthetic initialization, new session ID, internal network and new volumes.
Reuse the accepted application/PG17/n8n image IDs, local runtime, kernel and established
SDK -> signed relay -> PostgreSQL -> slot-worker path. No new scheduler or worker logic.
Project selection requires an additive harness change: the current controller hardcodes
Stage 2 physical state. Do not monkey-patch globals, relocate state or fake the original
project label to reuse the aborted journal. Existing drivers/migrations stay unchanged.

## Consolidated executable task

Entry point: `bash staging/laptop/run_recovery_only.sh` from the reviewed clean
development checkout, using the existing pinned PY/KERNEL. The harness is implemented
and offline-checked; disposable runtime acceptance remains NOT TESTED. Focused checks
cover namespace, timing, resume, receipt rejection and real CMS encryption of invented
bytes with mocked database calls.
Do not rerun accepted integration suites. Record reviewed runner/source hashes.

One session has durable prepare/arm/interrupt/recover/verify/export markers and an
exclusive controller lock. The same entry point is invoked after interactive login;
it resumes only at a known completed checkpoint, never retries a started-but-incomplete
phase or repeats approvals. Missing authorization, identity mismatch or uncertain state
stops execution with sanitized stage/exit results. Recovery deadline checks occur before
phase reservation. No application or Windows startup registration.

Owner intervention is limited to: confirm attendance and observer readiness; perform
one normal Windows reboot when prompted; log in and manually launch Docker/WSL and the
approved attended monitor bridge; rerun the same task; copy exactly two encrypted USB
payload files to ThinkPad; run the single supplied restore command. No hidden credential
entry or SMB configuration is needed. Allow about 25–35 minutes plus USB handling.

## Fresh fixture and timing outline

Use actual wall time and minute-aligned synthetic civil appointments. All approvals
are fresh and go through the accepted SDK/signed relay/owner-confirmation flow.

- T+1: one paired pre-outage reminder, recorded before interruption.
- T+2: silent appointment; no slot or delivery attempt.
- T+3 and T+4: two reminders due while the fresh stack is intentionally stopped.
- T+16: one post-recovery paired reminder.
- T+17: one simulated uncertain attempt, with no receipt and no automatic resend.

Stop only the new stack after the first receipt and before the outage due times.
Record stop completion and pre-reboot Windows boot identity. Owner reboots once;
remain at login through T+4, then log in and start the approved host tools manually.
Show exact local times and deadlines before requesting reboot. No sleeping at a login
screen based on ambiguous relative times. Do not alter system clocks or due dates.

If readiness is slower than the performance target, record it honestly and assess
functional results separately. Expired timestamps, insufficient due-in-outage evidence,
unsupported worker lookback or unsafe state are not repaired by rewriting fixtures.

## Revised acceptance criteria

| Gate | Proposed criterion |
| --- | --- |
| Physical lid | Retain original successful interval/open checks and receipts; correlate preserved observer log, no repeated lid exercise |
| Windows recovery | Independently verify boot identity changed exactly as expected; no pre-login active recovery-only application services |
| Manual startup performance | Report elapsed stop-to-signed-health-ready, stop-to-first-recovered receipt, overdue duration, login time (owner reported), and observer recovery. Target signed health ready within **600 seconds of controlled stop completion**, inclusive of reboot/login/Docker/WSL/startup; do not restart the timer at login |
| Functional catch-up | Both genuinely overdue reminders each reach exactly one paired recorder/SQL receipt within 120 seconds of signed application/worker readiness, inside the unchanged six-hour worker eligibility window; due dates stay unchanged |
| Timing independence | If 600 seconds is exceeded, performance FAIL; functional checks may continue only within unchanged safe eligibility and approved fixture scope. No overall unqualified PASS if a required timing gate fails |
| Delivery result | Four total paired sent receipts (one before, two overdue, one post); one uncertain attempt without receipt; zero silent attempts and no legacy delivery duplication |
| Durable history | Pre-outage receipt/approval IDs and rows preserved after reboot. Immutable snapshots, attempts and receipt pairs remain consistent |
| Restart/duplicate safety | Subsequent worker ticks and one controlled application/worker restart preserve all five attempts and four receipt pairs; uncertain is not retried. No additional Windows reboot |
| Single worker | Exactly one normal worker holds the advisory lock; competing worker exits 75 without claim or send |
| Observer | Existing host-key/key restrictions retained. New session log explicitly identifies the new project and reviewed revision; fresh healthy samples before arming, outage and recovery samples recorded. No repeat of SSH restriction acceptance |
| Export | Writers quiesced; six histories hashed; exact pinned public recipient certificate still valid; stream directly from pg_dump to CMS AES-256-GCM, no plaintext dump; one-use local ciphertext publication and manifest |
| USB transfer | Owner identifies exact removable device/folder before copying only ciphertext and restore-manifest; independently record and verify both SHA-256 hashes before/after transfer; no credential/key/config copy |
| Independent restore | ThinkPad pinned independent daemon and PG17 image, no app/poller/worker; transient networkless restore; migration checksums, six histories, four sent and one uncertain match; remove only transient recovery container |
| Closeout | Stop only recovery-only stack; retain state/evidence. Compare original aborted and Stage 1 inventories; scoped monitoring/SMB cleanup separately recorded |

The original evidence() helper enforces delivery within 180 seconds of due time.
Do not edit it or use it for the new delayed-catch-up assertion. A focused continuation
assertion must retain every status/attempt/identity/receipt check while measuring genuine
overdue catch-up relative to recorded recovery readiness. Test boundary times and prove
an invalid receipt, duplicate, stale lease or uncertain resend still fails. This changes
test acceptance timing only, not retry, lease, lookback, quarantine or worker behavior.

## Monitoring and USB amendment adaptation

The current bridge and observer pin `dincharya-stage2-physical`; they cannot honestly
monitor the new namespace unchanged. Prepare the smallest session-specific status target
change and observer expected-project option, both exact-allowlisted. Retain forced
read-only command, pinned SSH identities, restricted source IP, signed application-derived
health, stale-response rejection, non-admin account and no Docker privileges. Verify
correct target and fresh samples, without reinstalling SSH or repeating restriction tests.
Old and new observer logs must remain separate. No fabricated ready/outage samples.

Reuse the USB amendment's existing certificate pin, ThinkPad-only key custody,
independent digest channel and restore format. Adapt the companion export guards to the
new namespace/journal rather than setting the aborted physical session to verified.
The existing physical_restore.py can verify the same manifest/history format from local
ThinkPad storage; retain no-network/no-host-port PostgreSQL recovery. No SMB mounting,
third-device connectivity requirement or new SMB configuration. SMB isolation/transfer
remains **NOT TESTED / DEFERRED — superseded by owner-mediated USB for this session**.

Review only previously created receiver account SID, share path and exact two temporary
backup firewall rules against original metadata before scoped cleanup; stop on mismatch.
Preserve existing firewall rules, Public profile and all recovery files/private key.
Do not claim cleanup until actually verified.

## Approval and remaining gates

Owner approval recorded for one fresh recovery-only synthetic session, the additive
isolated harness/status namespace adaptation and revised functional/timing criteria
above, one additional supervised Windows reboot, and owner-mediated transfer of exactly the CMS ciphertext
and integrity manifest to the already approved ThinkPad recovery destination using an
explicitly identified USB device/folder. Confirm exact USB device/folder locally before
copying. No repeated lid test; no modifications to aborted run; no production, Telegram,
SMB expansion, automatic startup, deployment or merge. A source/security defect still
requires a focused fix and checks, never weakened assertions or repeated blind sends.


## Executable operator sequence

Run from the newly committed reviewed revision, clean on Acer and ThinkPad. Keep the
original report and all original artifacts. Do not run the old physical driver.

1. Set `REV` to the new reviewed commit, `PY`/`KERNEL` to the already verified local
   values. Set `CERT` to the retained public certificate, `CERT_SHA256` to the exact
   previously approved DER fingerprint, and `USB_STAGING_PARENT` to the approved
   owner-only tools directory. These public/local path values stay outside Git.
2. `bash staging/laptop/run_recovery_only.sh` prepares only the fresh namespace and
   returns NOT ARMED. No fixture is submitted on this first call.
3. Close the previous attended bridge. Use the privately retained, syntax-checked
   `Set-RecoveryMonitorTarget.ps1 -Revision <new reviewed commit>` once in owner
   Administrator PowerShell. It backs up and retargets only the two bridge scripts;
   no SSH/firewall/account changes. Launch the bridge manually. Do not run the updater
   again after reboot; manually launch the already updated bridge instead.
4. On ThinkPad use the existing pinned SSH wrapper/config, but a fresh log and the
   updated observer command:

       python3 -B staging/laptop/observer.py dincharya-stage2-acer \
         --stage2-revision "$REV" --stage2-project dincharya-stage2-recovery-only \
         --samples 240 > "$NEW_OBSERVER_LOG"

   Verify at least three consecutive fresh healthy, zero-count samples and retain
   original logs. Existing wrapper/config must still be explicitly selected via PATH
   or the previously pinned SSH alias; do not assume a temporary wrapper is persistent.
5. With owner attending, set `OWNER_ATTENDING=1` and `OWNER_OBSERVER_READY_UTC` to the
   UTC epoch of the most recent independently checked healthy sample (not guessed local
   time). Run the same entry point within 45 seconds. It arms once, waits for the first
   paired receipt, stops the new stack and prints an exact login-not-before time and
   performance deadline. Owner performs one reboot and follows that prompt. No lid test.
6. After interactive login manually start Docker Desktop and the attended SSH bridge.
   Restore variables and rerun the same entry point. It checks changed boot, due dates,
   stopped stack and lookback BEFORE reserving recovery. A delayed but safe recovery
   can complete functionally; the 600-second target result is kept separately.
7. The task waits through the final uncertain fixture. If `OBSERVER_LOG` is absent,
   it returns WAIT before reserving verify. Stop the independent observer, copy only
   its sanitized JSONL to a new private Acer path, set `OBSERVER_LOG`, and rerun.
8. Verification checks all outcomes, competing-worker exclusion and controlled service
   restart/no resend, then quiesces writers. Set `APPROVED_STAGE2_USB_EXPORT="$REV"`
   only within the approved USB scope and rerun with the same certificate/parent inputs.
   The new task exports exactly ciphertext plus manifest locally and stops Stage 2.
   Do not invoke the old physical USB companion or original physical export.
9. Identify exact USB device/folder with owner, copy only the two export files and
   independently verify both SHA-256 values at each handoff. On ThinkPad use existing
   `physical_restore.py` with the NEW reviewed REV, local ciphertext directory, manifest
   and independent manifest hash, retained private key and pinned independent PG17/daemon.
   No application service runs on ThinkPad. Record actual restore exit and summaries.
10. Record source task exit, performance and functional results separately. Exit 2 means
    the source task completed functionally/exported but missed startup performance;
    exit 1 is a safety/functional failure. Overall acceptance also requires successful
    independent restore and integrity verification. An intermediate WAIT/prepare exit 0
    is not final acceptance.

For diagnostics use the same entry point with `inspect` or `status`. On failure stop
advancing, interrupt the active task if necessary, then use its `stop` action to mark only
this new session aborted and stop its services. Preserve all state; never delete phase
reservations. No global Docker cleanup. The aborted original is only fingerprinted
read-only, never restarted or exported.

## Offline checkpoint

18 new focused tests passed, including real OpenSSL CMS round-trip of invented bytes
with mocked service/database calls, exact two-file publication and one-use export.
Affected existing staging checks passed. Shell/Python/PowerShell syntax checks passed.
The repository source scanner does not allow `.ps1` paths; the operational monitor
updater is retained privately outside Git rather than weakening that scanner or staging
an unaccepted source file. Its syntax and exact target-change code were reviewed; it
has not been executed. All repository candidate files use the existing source scanner.
No runtime, reboot, new fixture, monitoring target switch, SMB mount or transfer occurred.
