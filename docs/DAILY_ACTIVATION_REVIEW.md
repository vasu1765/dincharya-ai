# Acer personal daily activation review

## Accepted evidence

The disposable bounded live session passed at
`dc7335db10cd2ff2ef4fe02714dd0c6b27418c3e`. The owner observed the
historical Delhi answer, both previews and original-message confirmations,
silence for the silent appointment, and exactly one at-start reminder.
The read-only audit exited 0. It matched the private manifest to the consumed
one-use release and found three send receipts, two edits paired to their
original previews, two active one-offs at the approved times, and one sent
at-start slot and its matching attempt receipt. The slot settlement time
was within the approved window, after its due time and before the planned
shutdown. The owner observed arrival time. The UI ledger records reservation
time and settled receipt state.

There were four distinct new message receipts, zero duplicate deliveries,
zero uncertain or unsettled records and no silent slot. STOP was present.
The operator container, gateway/worker connections and both advisory locks
were gone. The bounded authority row remains enabled in the preserved
disposable database. The release is consumed and expired. All three earlier
ledgers and their fences matched; Docker inventory was unchanged during
audit. Preserve the four ledgers and keep their sessions fenced.
[Owner and coordinator checkpoint](https://github.com/vasu1765/dincharya-ai/pull/18#issuecomment-7199381004)

Carry forward the native daily gate at `190667c` and supervised evidence at
`624327f`. The bounded session qualifies its live messages and lifecycle.
Ordinary daily mode, the persistent host setup and the selected off-device
destination still need qualification.

## Shortest path to activation

| Gate | Qualification before proceeding |
| --- | --- |
| Target and ownership | Pin the exact reviewed Git revision, release checksum manifest, Acer daemon and three unchanged local image IDs. Verify exclusive custody of the dedicated bot, exact private recipient, clean queue and no competing poller or webhook. Verify one operator, protected non-root UID/GID, source export and STOP. Confirm Acer AC behavior and manual recovery after interactive login. |
| Empty storage | After separate authorization, inspect or create only the named personal PG17 and relay volumes, verify identity, labels and emptiness, and bootstrap only personal migrations 0001–0005 with their exact checksums. Leave authority unprovisioned and STOP present. Verify SCRAM on private TCP, role grants and NOLOGIN operator/executor. Mount only the gateway and worker keys in the operator. |
| Relay and observer | Verify DB and n8n attach only to the internal bridge, publish no ports, and have no unrelated peers. Give only the operator outbound access, using the previously reviewed ordinary Docker egress profile if approved again for daily use. Install the single reviewed relay workflow into the new n8n instance and verify a signed synthetic echo and rejection of a forged request before credential provisioning. The n8n local Server CLI import and publish route is a candidate for exact-image qualification. Keep the bounded HTTP cookie setting confined to the bounded fixture. From the approved observer path verify aggregate health only, fresh samples, and outage alerts when the Acer becomes unreachable. |
| Backup and restore | Privately pin an off-device mount path and exact `findmnt` source, owner-only archive directory, recipient PEM digest and independent key custodian. Qualify permissions, hard-link publishing, free space and independent digest storage. Verify /dev/shm is tmpfs with capacity for the dump plus ciphertext on the recovery host and review WSL swap handling. Use synthetic data to verify the exact destination and current helpers once, then decrypt on the recovery host with its own verified PG17 daemon into an empty networkless tmpfs target. Compare migration register, schedules, occurrences, slots, attempts and UI histories. Verify fenced authority, old approvals invalid, no application roles with LOGIN, and no service startup. |
| Daily authorization | When the preceding gates pass, approve a fresh private manifest for the reviewed revision with `profile=daily`, empty commands, one owner/bot, and a finite start/end. Use a five-minute catch-up for existing materialized slots if approved. Choose attended manual foreground startup for the first window. Keep login registration and backup scheduling outside the initial approval. Review one daily operation window before considering unattended startup. |

[n8n Server CLI workflow import and publication](https://docs.n8n.io/deploy/host-n8n/configure-n8n/use-the-command-line/)

The owner decisions can be taken together. Confirm Acer as the sole active
host, the dedicated bot and private recipient, the first finite authorization
window, ordinary outbound access, the five-minute catch-up, and the exact
off-device destination, recipient certificate and custodian. Make a
separate decision if interactive-login registration or a scheduled backup
is wanted later.

For a stop or outage, place STOP in the private operator root and verify both
locks and runtime connections disappear. Preserve every receipt. Review
uncertain and overdue slots before restarting. For a restore or host change,
fence the old host first, compare the restored histories and require a fresh
authority epoch and release. Never run a second active copy or replay an
uncertain delivery. Keep the original volumes and ciphertext for rollback.

The daily scope is civil appointments and reminders plus read-only Delhi
Panchang. Personal lunar scheduling, festival rules, 2B source adoption,
production promotion and merging remain separate gates.

## Persistent preparation checkpoint

The owner authorized the fresh Acer environment, same dedicated bot,
ordinary operator outbound access, manual startup, a seven-day initial
daily window and five-minute catch-up. The backup policy is encrypted
Google Drive daily with seven daily and four weekly recovery points.
Activity tracking and a web dashboard are outside the selected profile.
[Owner authorization](https://github.com/vasu1765/dincharya-ai/pull/18#issuecomment-7199827092)

| Qualification | Result |
| --- | --- |
| Existing acceptance | All four ledger fences and aggregate counts rechecked against the approved daemon. Preserved resources and images retained. |
| Fresh storage | Created the two approved named volumes and started only PostgreSQL 17 and n8n on an unpublished internal bridge. Applied exact personal migrations 0001–0005 and recorded their hashes. No bot key, authority, release or operator present. |
| Database boundary | Native SCRAM over private TCP with four scoped keys. Wrong password rejected. Gateway and worker acquisition denied with no authority. Observer could read only aggregate health. Backup could read its granted ledger and could not mutate authority. Reconciliation and executor logins remain disabled. Existing exclusive lease evidence carries forward. |
| Relay | Pinned native n8n CLI imported and published the single reviewed workflow. Signed round-trip passed. The application receiver returned HTTP 403 for a forged signature and n8n surfaced the denial to the caller as HTTP 500. |
| Acer readiness | AC connected, do-nothing lid action, and AC standby and hibernate timeouts disabled at inspection. Local readiness failed during a deliberate stop of the new relay and recovered when the same container restarted. Independent observation of an Acer outage still requires the designated observer. |
| Backup tools | Local AES-GCM CMS qualification used the new empty PostgreSQL database, an invented local recovery credential and a networkless PG17 restore. Schema function signatures and empty history counts matched and all six restored roles remained NOLOGIN. Cleanup restored the Docker inventory. Populated-history rollback fencing carries forward from prior synthetic restore acceptance. |
| Real backup destination | Pending owner-selected Drive OAuth, folder pin and independent key custody/recovery. No Drive files were listed or transferred. |

### Google Drive procedure

Use an owner-only local Linux spool with normal filesystem semantics.
`scripts/daily-backup.sh --spool` reads through the scoped backup role,
checks the dump using PG17 tools, uses verified tmpfs for plaintext scratch,
and publishes only authenticated CMS ciphertext to the spool.

The proposed transfer uses the Drive API through a dedicated rclone remote.
Pin the folder ID. Create the folder with the same app if the
`drive.file` client cannot see an existing browser-created folder.
The owner performs OAuth locally. Use a dedicated client and configuration
with only the `drive.file` scope. Keep authorization material outside the
operator mount and Git. The official Linux amd64 rclone v1.76.0 executable
was verified against the published archive SHA-256
`b00f00b3266c3764413afe599d3ec316f6f43b3e0ea8a0bc1d186d2133e46df7`.
[rclone Drive scope and root options](https://rclone.org/drive/)

```bash
bash scripts/daily-backup.sh --spool "$DB" "$SPOOL" "$RECIPIENT_PEM" "$RECIPIENT_PIN"
python3 -B scripts/daily-drive-upload.py "$SPOOL/$DIGEST.cms" \
  --config "$PRIVATE_DRIVE_CONFIG" --folder "$APPROVED_FOLDER_ID" --rclone "$RCLONE"
```

The uploader validates the local CMS and digest, then uses immutable copy
and streams back the exact remote object for an independent SHA-256
comparison. It exposes only the digest or a sanitized failure class.
Focused tests used real OpenSSL CMS with a mock Drive client to verify the
bounded read-back and denial of plaintext, symlinks, wrong scope or folder,
and corrupted remote bytes. The Google Drive service qualification remains
pending until one synthetic archive succeeds through the actual remote.

For the first remote qualification, use the empty source or invented
fixture, verify exactly one uploaded ciphertext, independently record its
digest, then retrieve that exact object on the approved recovery host.
Restore with the independent key into networkless, disposable PG17.
Report migration register, aggregate comparisons, epoch and role fences,
and cleanup. Keep the key outside Google Drive and the application host.
Keep retention report-only and start with manual backup invocation.

### Final owner checkpoint

- Confirm the dedicated Drive OAuth client and folder pin through local
  instructions, with credentials held in its separate protected config.
- Confirm the independent recovery host and recipient certificate fingerprint.
  The same host may run the attended external observer if permitted. Agree
  on the narrow status connection and observe both readiness and outage
  from that host before activation.
- After these gates pass, select the exact IST start for the seven-day window
  and approve the resulting private manifest digest. Keep STOP in place
  until deliberate manual startup. Registration, personal backup scheduling,
  deletion and any scope expansion remain separate decisions.


## Acer-only initial release

The owner elected to proceed on Acer while ThinkPad is unavailable.
ThinkPad restore, independent availability monitoring and transfer of key
custody are **DEFERRED**. Carry forward local encrypted PG17 restore,
aggregate observer permissions and local relay outage/recovery evidence.
Keep the seven-day startup attended and manual, with a five-minute
missed-reminder catch-up and a separate exact manifest approval.
[Coordinator checkpoint](https://github.com/vasu1765/dincharya-ai/pull/18#issuecomment-7237038780)

The remaining Acer qualification is one real synthetic Drive round-trip
into the dedicated `Dincharya-AI-Backups` folder using owner-local,
file-scoped OAuth. Before key creation, agree on the exact mounted
removable device. Place the passphrase-encrypted recipient key directly
on the agreed offline device and keep its passphrase separately. Only
the public certificate remains on Acer. After the exact remote
ciphertext SHA-256 matches, test that the offline copy decrypts it and
eject the recovery medium before recording the qualification. The key
and OAuth material stay outside Drive and the operator bind mount. Drive
receive, independent media custody, and final release remain pending
until completed. No backup scheduler or retention deletion is active.

The private Acer-only runbook covers OAuth, ciphertext qualification,
safe media detachment, and the existing prepare/approve/provision/start/stop
sequence. Keep STOP in place until the owner authorizes the settled
seven-day manifest. Use the local aggregate status command during the
initial operation window. The prior four ledgers are preserved.
