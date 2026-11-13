# Dincharya Telegram Gateway

Use Python 3.12. Copy `.env.example` to `.env` and configure locally. Never share the token.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python gateway.py
```

The n8n workflow must have a POST Webhook with path `dincharya-chat`, followed by Basic LLM Chain (Prompt: Define below; user message `{{ $json.body.message }}`) with Ollama Chat Model attached. Then add `Edit Fields` node with `reply` = `{{ $json.text }}` and `Respond to Webhook` with JSON response `{{ $json }}`. Set Webhook response mode to `Using Respond to Webhook Node`, publish workflow, and use production webhook URL.

Security: Gateway restricts Telegram user ID, but n8n webhook itself is not authenticated in this initial local-only prototype. Keep n8n bound to localhost and do not expose the webhook publicly. Before VPS deployment, add a shared secret/authentication and network restrictions.

## Isolated reminder acceptance

Run from the repository root with
`PYTHONPATH=. python telegram-gateway/gateway.py --acceptance`.
Start with a dedicated test bot, a private test chat, and an empty disposable
PostgreSQL database on an unused loopback port other than 5432. Apply all four
numbered migrations using the isolated migration runner so the ledger is present.
Provide these settings from a clean shell using the test credentials only.

| Environment variable | Value |
| --- | --- |
| `DINCHARYA_TEST_BOT_ID` | Numeric ID of the dedicated test bot, independently verified |
| `DINCHARYA_TEST_BOT_TOKEN` | Token issued for that test bot |
| `DINCHARYA_TEST_OWNER_ID` | Numeric owner ID for the private test chat |
| `DINCHARYA_TEST_PG_PORT` | Dedicated loopback port for the disposable PostgreSQL listener |
| `DINCHARYA_TEST_PG_PASSWORD` | Password for the disposable `synthetic_test` database role |

Acceptance skips dotenv, regular gateway configuration and n8n routing. It
rejects inherited regular gateway, PostgreSQL and HTTP proxy settings. It checks
the token against the supplied test bot ID, pins the DB to loopback and verifies
the test database name, role and migration ledger before polling. Verify the
pinned ID independently because a matching token and ID do not establish that a
bot is dedicated to testing. Use a single gateway and keep other delivery
systems off. The job allows one in-process invocation, and a PostgreSQL session
lock serializes delivery ticks from cooperating gateways on the same database.
Each tick claims at most one reminder.

1. Send `/remind YYYY-MM-DD HH:MM Acceptance check` with an Asia/Kolkata time a few
   minutes ahead. Record the proposal ID. Confirm the proposal is pending and no
   event or delivery has been created.
2. Send `/approve_reminder ID` from the same private chat before the due time.
   Confirm approval and a single event. Repeating the command should report that
   the request is already decided. To exercise rejection, submit a separate
   proposal and use `/reject_reminder ID`.
3. Wait for the due minute and confirm one plain-text Telegram reminder and a
   single `sent` delivery row. Check a second tick for duplicates.
4. Stop the test gateway and remove the disposable test database through its
   normal test teardown.

The gateway handles the explicit commands. In regular mode, ordinary chat
goes to n8n/Ollama. The first command supports one-time Gregorian reminders. Recurring
series and occurrence edits use the existing PostgreSQL proposal API. Definitive
Bot API rejections (400/401/403/404 with matching failure envelopes) follow the
database retry policy: 30/60/120/240-second waits and a five-attempt cap. HTTP 429
is quarantined using the existing `uncertain` state for manual recovery, even
when Telegram confirms rejection: the current database API cannot persist its
`retry_after` minimum wait. No immediate resend or sleep under a lease occurs.
Automatic rate-limit recovery requires a durable cooldown implementation; do not
manually retry before Telegram's wait expires. Timeouts, malformed responses and
5xx responses also remain quarantined for operator reconciliation.

## Delivery reconciliation

`PostgresReminders.list_quarantined(after_id=0, limit=20)` provides a bounded,
read-only transaction and metadata page for managed `uncertain` rows, ordered by delivery ID.
Pass the last returned delivery ID as `after_id` for the next page. Limits are
1–100; payload/title, chat identity, tokens and raw errors are excluded. Receipt
presence and an opaque row-state hash are included; timezone is locally fixed to
UTC for observation consistency. This adapter building block does not clear
uncertainty, change retry state or send.
It is not an operator resolution interface; all resolution/resend remains gated.

Migration 0004 persists the validated Telegram chat/message pair atomically with
lease-checked sent acknowledgement. The transport checks returned destination and
usable message ID; receipt fields are omitted from object repr/logging. The old
ack API and historical NULL receipts remain compatible; missing migration stops
gateway registration before ticks. No historical IDs are inferred. An HTTP or
commit acknowledgement can still be lost; do not resend based on client failure.
The inspection path cannot resolve such ambiguity automatically. See the
[proposed audited workflow](../docs/RECONCILIATION_DESIGN.md): no resolution/resend
operation is enabled, and owner approval is required before enabling one.

## Gated synthetic lunar application

New commands: /lunar_birthday FIXTURE, /lunar_anniversary FIXTURE,
/approve_lunar_rule TOKEN, /approve_lunar TOKEN, /reject_lunar TOKEN,
/cancel_lunar OCCURRENCE_UUID and /lunar_status OCCURRENCE_UUID. Only configured
synthetic fixtures are supported; no unvalidated calendar calculation. SDK owner
and private-chat checks precede signed n8n requests. Separate rule/occurrence
approvals are mandatory; cancellation also requires explicit review. Exactly
one reminder JobQueue owner may be registered; legacy and lunar polling cannot
run together. Existing ordinary gateway modes remain unchanged.

Install pinned optional acceptance dependencies from requirements-m2g.txt into an
isolated venv. Application uses real psycopg connections and the existing worker/
Telegram adapter; default delivery is disabled. The only live gateway mode is
--lunar-acceptance CONFIG --live-approved with a restricted outside-Git config
and independent dedicated test-bot verification. Do not run it without owner
authorization. [Runbook](../docs/M2G_TELEGRAM_ACCEPTANCE.md) prepares exactly one
private fixture reminder; [evidence](../docs/M2G_TELEGRAM_RESULTS.md) records
actual simulated-wire acceptance. No actual token was read or message sent.
