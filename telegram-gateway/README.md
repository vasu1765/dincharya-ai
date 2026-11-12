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
