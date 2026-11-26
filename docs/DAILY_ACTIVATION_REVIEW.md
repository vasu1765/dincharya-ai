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
