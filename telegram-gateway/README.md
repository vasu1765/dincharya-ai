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

Run from the repository root with `PYTHONPATH=. python telegram-gateway/gateway.py`.
For this check use a dedicated Telegram test bot, the owner's private test chat,
and a disposable application database with both numbered migrations applied.
Set `DINCHARYA_REMINDER_DSN` to that test database connection. Setting it enables
the worker for **all** due occurrences in that database. Start with an empty
synthetic schedule and a single gateway process. The worker polls PostgreSQL
every 15 seconds and claims one reminder per tick. Keep any other delivery worker
off during this check. Set the usual Telegram environment variables for the test
bot and test owner. Use an isolated n8n endpoint if exercising ordinary chat.

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

The explicit commands are handled by the gateway. Ordinary chat still goes to
n8n/Ollama. The first command supports one-time Gregorian reminders. Recurring
series and occurrence edits use the existing PostgreSQL proposal API. Definitive
Bot API rejections follow database retry policy. Timeouts and ambiguous responses
are quarantined for operator reconciliation.
