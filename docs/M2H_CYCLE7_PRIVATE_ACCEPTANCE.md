# Cycle 7 bounded private Telegram acceptance

Fresh owner approval is required before launching a live session. The earlier
M2G authorization is complete. The Cycle 7 exact-schema run passed separately
using simulated Telegram. [Accepted WSL evidence](https://github.com/vasu1765/dincharya-ai/issues/6#issuecomment-6970326525)

## Approval scope

Approve a single session on the reviewed wrapper commit and branch
`development/m2h-private-telegram-acceptance`. Use the dedicated
`dincharya_acceptance_test_bot` with its pinned numeric bot ID, and the owner's
existing one-to-one private chat whose ID equals the pinned owner ID. Keep both
IDs and the bot credential in the protected local file. The owner must ensure
exclusive use of the test bot during the window.

Set T0 to a whole minute between 08:00 and 20:49 IST. The approval window ends at
T0 + 11 minutes. Begin the launcher within 15 minutes before T0, allowing time
for the isolated stack to start. Submit the three commands in order and confirm
both civil appointments before T0 + 4 minutes. Use the approved civil date in
both commands.

| Owner action | Exact input | Expected bot chat messages |
| --- | --- | --- |
| Historical read | `/panchang 6 December 2023` | One answer. Zero writes to schedule, review and notification tables. |
| Silent appointment | `Schedule Acceptance silent on YYYY-MM-DD at HH:MM; none` with time at T0 + 6 minutes, then click Confirm | One preview and one confirmation. No delivery row or attempt. |
| At-start appointment | `Schedule Acceptance reminder on YYYY-MM-DD at HH:MM; at start` with time at T0 + 8 minutes, then click Confirm | One preview, one confirmation and exactly one reminder during the scheduled minute. |

The outbound cap is six chat-message attempts, including at most one reminder
attempt. Successful acceptance requires all six acknowledged chat messages,
including one genuine reminder with a paired database receipt. Callback
acknowledgements have no chat-message text. The wrapper verifies the recipient
and the actual bot in each chat receipt and checks the ledger at the silent
minute, the reminder minute and twice afterward. The owner separately confirms
the two appointment outcomes on their device.

## One WSL execution instruction, after authorization

In the authorized WSL checkout, switch to the reviewed branch at the approved
full SHA and verify a clean working tree. Use the pinned local Python environment
and verified public ephemeris. Create one local, owner-owned JSON file outside
Git in an owner-only directory with file mode 0600. Set the following keys to
the exact approved values. Avoid posting the populated file or any numeric
recipient, token or receipt in chat or Git.

```json
{
  "approval": {
    "revision": "<full approved commit>",
    "start_ist": "<approved YYYY-MM-DDTHH:MM:00+05:30>",
    "bot_username": "dincharya_acceptance_test_bot",
    "bot_id": 202,
    "owner_id": 101,
    "chat_type": "private",
    "message_cap": 6,
    "reminder_cap": 1
  },
  "telegram": {
    "token": "<dedicated test bot credential>",
    "bot_id": 202,
    "owner_id": 101
  }
}
```

The numbers above are examples. Use actual identities only in the protected
local file. Keep the existing daemon and exact authorized schema. From the
repository root, run once with the approval file and full approved SHA supplied
in the named environment variables.

```bash
OPENBLAS_NUM_THREADS=1 python -B tests/integration/m2h_private_telegram.py \
  --approval-file "$DINCHARYA_PRIVATE_APPROVAL_FILE" \
  --expected-revision "$DINCHARYA_PRIVATE_APPROVED_REVISION" \
  --expected-daemon-id 44c1ef83-c50e-4ecc-8f19-4b112bc40f29 \
  --ephemeris "$DINCHARYA_PUBLIC_DE440S" --execute-approved --live-approved
```

The launcher reserves one attempt at the window and owns the existing isolated
three-service test project for its lifetime. It verifies the signed native relay,
fresh database and database clock before contacting Telegram. It accepts only
the two review tickets issued within this session and invokes the existing
advisory-locked worker. The owner custody requirement covers separate hosts.
The wrapper checks for a webhook, stale queue and polling conflicts, and stops
on any unexpected update.

## Simulated validation

Nine focused recorded-I/O tests passed. Two disposable runs with real
PostgreSQL 17.12 and native n8n 2.47.3 passed. The success case produced six
simulated sends, one paired receipt and zero silent sends. The failure case
returned a simulated Telegram 429, leaving one quarantined attempt and no
retry or receipt. Both disposable databases shut down. The CLI refused
startup without the explicit approval flags.

## Stop and evidence

Stop on a mismatched revision, database, signed relay, bot, private recipient,
window, message, approval, worker lock, slot or receipt. Rejection, rate limit,
timeout, uncertainty and extra traffic all end the session. The worker
quarantines an unconfirmed reminder. Preserve the one-use reservation and never
restart or resend the same window. Treat a failure after a send as unconfirmed
until the device and ledger evidence can be reconciled separately.

The protected test runner cleans up its disposable processes, containers and
database. The owner keeps the approval file private and handles the credential
under local custody. Report only fixed stage headings, exit code, outbound
count, receipt present or absent, silent/reminder counts, owner device
confirmation, and teardown status. General live scheduling, production, source
promotion and merging require separate authorization.

## Completed authorized private session — 18 November 2026

**PASS — exit 0.** One wrapper execution at the approved clean revision
`72286479d8b52aa0e5b34c3c2db19f14883281eb`, within the authorized
12:15–12:26 IST session. The protected approval used the dedicated test bot and
existing locally pinned private recipient. Credentials and numeric identities
were not printed or stored in Git.

- Exact revision, pinned public ephemeris/dependencies, daemon, isolated services,
  original schema initialization, migrations, scoped roles and signed relay passed.
- Owner confirmed both appointment approvals before the deadline.
- **Six chat attempts, six acknowledgements, one reminder attempt, one paired
  database receipt, zero silent reminders and no duplicate reminder.**
- The wrapper checked the silent minute, reminder minute and two subsequent
  worker ticks, and checked the authorized schema bytes unchanged.
- Owner explicitly confirmed six total messages, exactly one reminder, no silent
  reminder and no duplicate through the end of the approved window.
- Wrapper exit 0; disposable teardown verified; unrelated running-container
  inventory unchanged. No source correction, retry, restart, resend or delivery
  history reset was needed.

This one-use authorization is complete. Preserve its reservation. The protected
approval file and dedicated credential remain under local owner custody outside
Git. No further Telegram operations are authorized by this evidence. Production,
source promotion, deployment, merging and general lunar scheduling remain gated.
