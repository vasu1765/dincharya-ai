# Receipt and adversarial API checkpoint — 2026-11-13

Branch `development/m2-recovery-acceptance`, pushed base `db87193`. New changes
remain uncommitted while sandbox Git metadata is read-only. No live Telegram,
n8n or completed full integration suite was repeated.

## Focused evidence

| Check | Result |
| --- | --- |
| gregorian_adversarial.sql | PASS: malformed fields/rules, invalid action/scope/identity and null requester, non-Gregorian rules rejected; unauthorized/absent requests, invalid horizon/decision and null-force protection; event/rule/override staleness even with force, atomic failure, explicit discard and replay rejection |
| adversarial-concurrency | PASS: conflicting adds, two updates of one snapshot, approve/reject of one request and unauthorized/authorized races each preserve a single valid outcome |
| Receipt upgrade | PASS: seeded historical sent row unchanged apart from new nullable columns; no IDs invented; four-argument acknowledgement body unchanged; prior migrations/checksums and legacy function properties retained |
| telegram_receipts.sql | PASS: wrong token/expired lease/partial or wrong-outcome receipt rejected; atomic status/receipt; replay cannot overwrite; old worker can acknowledge with NULL IDs; duplicate pair rolls back sent update, expires to quarantine and cannot be reclaimed; message IDs scoped by chat; row change invalidates observation version |
| receipt-concurrency | PASS: competing acknowledgements accept exactly once, retain the winning pair, release token and prevent duplicate claim |
| Worker/adapter/config checks | 26 unique tests PASS across focused runs: 12 worker, 11 adapter and 3 existing acceptance-config checks; new coverage includes typed receipts, wrong destination/unusable IDs, acknowledgement/commit failure without replay, private identifiers hidden in receipt repr and read-only UTC inspection |
| Mocked gateway startup | 2 PASS using existing temporary gateway virtualenv; missing receipt migration blocks registration, regular opt-in checks migrations; no polling or API call |
| Migration-renderer and runner preflight | 4 + 3 PASS after registry/migration changes |

The adversarial matrix was extended once and only that changed SQL case rerun.
The previously pushed D10/legacy and old reminder suites were not rerun. Existing
migrations 0001–0003 were not edited. Every runtime run verified the pinned daemon
and image and used fresh PostgreSQL 17 with read-only root, tmpfs storage, no
network/ports/host mounts. The exact previously authorized schema input was read
unchanged; no neighboring backup files or credentials were accessed. Disposable
containers were removed and original running container IDs remained unchanged.

## Implementation and limits

Migration 0004 adds nullable `telegram_chat_id`/`telegram_message_id`, paired-value
and state constraints, and unique chat/message identity. New acknowledgement
delegates the original lease check and atomically writes the receipt; any receipt
constraint failure rolls back the status transition. The old API remains usable
with NULL receipt fields for old workers. New Telegram transport validates the
returned chat equals the configured destination and message ID is a usable
positive integer. [Telegram documents message ID scope and unusable zero IDs](https://core.telegram.org/bots/api#message).
The gateway now requires all four migrations and the new function before ticking.

No real HTTP send was tested. Synthetic SQL and mocked adapters prove the scoped
contracts above, not external exactly-once delivery or every database/network
failure permutation. Lost HTTP responses or commit acknowledgements still require
inspection, never blind replay. Historical IDs cannot be recovered retroactively.
Read-only inspection provides metadata, receipt presence and a UTC state hash;
it does not reveal receipts/payloads or enable resolution, reset or resend.

The [audited reconciliation design](RECONCILIATION_DESIGN.md) is ready for owner
review; metadata resolution and any resend remain explicitly disabled pending
approval. Full 2D/2E closure and later Milestone 2 source/Panchang/operational
acceptance remain subject to their documented exit criteria. No production
access, deployment or merge occurred.
