# PR #1 focused acceptance — 2026-11-13

Tested source: `aa05dd280ff6c90c510bc60c7351d1503a825cac` on
`development/telegram-reminder`. Existing local documentation/helper changes
preserved. PR remains draft; no merge or deployment.
Sanitized evidence is also posted on [PR #1](https://github.com/vasu1765/dincharya-ai/pull/1#issuecomment-6846033279).

| Check | Observed result |
| --- | --- |
| Expected Docker daemon identity and Desktop/Linux metadata | PASS |
| Pinned local PostgreSQL image, major 17 | PASS |
| Disposable database, synthetic role, initially empty public schema | PASS |
| Read-only root, tmpfs-only storage, network disabled, no ports/host mounts | PASS |
| Exact authorized schema validation/load and unchanged input bytes | PASS |
| Exactly two checksummed migration entries; repeat application | PASS |
| Reminder SQL, pending approval and five-attempt retry cap | PASS; script rolled back |
| Parallel duplicate decisions | PASS; one true, one false |
| Competing reminder claims and acknowledgement | PASS |
| Advisory lock contention, disconnect release and reacquisition | PASS on corrected lock-only run |
| Cleanup | PASS for each run; disposable containers/networks removed, original running container IDs unchanged |
| Gateway dependencies and synthetic job queue | PASS; temporary virtualenv, no network call during construction |
| Host loopback database connectivity | PASS; psycopg authentication, exact DB/role/version, two migrations and empty proposal/delivery ledgers |
| Private credential file | PASS; current-user-owned regular file 0600, parent 0700, no symlinks; no contents displayed |
| Dedicated bot identity | PASS; getMe matched independently confirmed test bot and replacement token ID |
| First owner-approved delivery | PASS; explicit owner Telegram approval before event creation; owner confirmed exactly one reminder |
| Gateway tick suppression and post-send duplicate observation | PASS; no attempts through due +35 seconds under lock; one send after release; unchanged ledger for 35 further seconds |

Initial lock harness timed out reading buffered psql output. This was a harness
failure; acquisition itself was not judged. Corrected to one output row and
repeated only the lock check in a fresh isolated container. SQL tests were not
repeated. The later live run separately verified gateway tick behavior.

## Live acceptance

The owner explicitly authorized one live end-to-end test. The dedicated bot
identity and exact private credential-file permissions were reverified. One
poller used a fresh disposable PostgreSQL 17 database with its own bridge network,
read-only root, tmpfs storage and only 127.0.0.1:55432 published. Exact migrations
and initially empty proposal/delivery ledgers were checked through host psycopg.

Observed one pending proposal with null event ID and no deliveries before owner
approval. The owner sent `/approve_reminder 1` in the private test chat, then one
event was created for 2026-11-13 12:01 Asia/Kolkata. The held advisory lock blocked
attempts until 35 seconds after due time, covering at least two 15-second ticks.
After disconnecting the lock holder, one send was acknowledged and persisted:
`status=sent`, `attempts=1`, `sent_at` present, `worker_token` null. The owner
confirmed exactly one reminder in the chat. The ledger stayed unchanged for
35 further seconds. No replay command or second proposal was sent.

Gateway shutdown and lock reacquisition passed. Disposable container and network
were removed, the loopback port closed and original running container IDs stayed
unchanged. No existing service was used. No production credentials or production
schema mutation, n8n startup, deployment or merge occurred. Only the exact
owner-authorized schema input was accessed read-only and remained unchanged.
No backup directory scan occurred. Credential values, private chat identifiers,
raw logs and schema bytes are excluded. The original owner-supplied secret file
is retained outside Git; gateway processes and temporary runtime files are gone.
Execution harness scripts and the acceptance virtualenv remain under `/tmp`;
no raw gateway log was retained.

HTTP logs were disabled during acceptance. Further Telegram sends require new
owner authorization. This finite one-time acceptance does not certify all 2D/2E
recovery/legacy paths or external exactly-once delivery. Checksum-corruption
rejection and replay-command behavior were not exercised in this acceptance.
