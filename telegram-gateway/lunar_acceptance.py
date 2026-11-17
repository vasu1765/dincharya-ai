"""Explicit live acceptance entry; never selected by the regular gateway mode."""
import httpx
import os
import logging
from urllib.parse import quote
from telegram.ext import Application
from dincharya.lunar_runtime import read_private,validate_test_bot
from lunar_handlers import OrchestrationClient,register_lunar,register_lunar_previews


def _config(path):
    if any(k.startswith('PG') or k.lower() in ('http_proxy','https_proxy','all_proxy','ssl_cert_file','ssl_cert_dir') for k in os.environ):
        raise SystemExit('Clear inherited PostgreSQL/proxy/certificate settings')
    return read_private(path)


def _verify_bot(info, owner_id):
    validate_test_bot(info, owner_id)
    token = info['token']
    class PrivateFormatter(logging.Formatter):
        def format(self,record):
            return super().format(record).replace(token,'[redacted]').replace(quote(token,safe=''),'[redacted]')
    logging.basicConfig(level=logging.WARNING,force=True)
    for handler in logging.getLogger().handlers:handler.setFormatter(PrivateFormatter())
    for name in ('telegram','httpx','httpcore'):logging.getLogger(name).setLevel(logging.CRITICAL)
    with httpx.Client(timeout=10,trust_env=False) as identity_client:
        response=identity_client.post('https://api.telegram.org/bot'+token+'/getMe');body=response.json()
        result = body.get('result', {})
        if (response.status_code != 200 or body.get('ok') is not True
                or result.get('id') != info['bot_id']
                or result.get('username') != 'dincharya_acceptance_test_bot'):
            raise SystemExit('Dedicated test bot verification failed')


def run_live(path):
    config = _config(path)
    if config.get('live_gateway_approved') is not True or config.get('delivery_enabled') is not True:
        raise SystemExit('Explicit private Telegram acceptance approval is required')
    info = config['telegram']
    _verify_bot(info, config['owner_id'])
    client=httpx.Client(timeout=30,trust_env=False,transport=httpx.HTTPTransport(uds=config['n8n_socket']))
    app=Application.builder().token(info['token']).build()
    register_lunar(app,info['owner_id'],OrchestrationClient(client,'http://n8n/webhook/m2g-lunar',config['command_key']),
                   OrchestrationClient(client,'http://n8n/webhook/m2g-lunar',config['tick_key']))
    try:app.run_polling(drop_pending_updates=False)
    finally:client.close()


def run_development(path):
    config = _config(path)
    if (config.get("development_astronomy") is not True
            or config.get("development_telegram_approved") is not True
            or config.get("delivery_enabled", False) is not False):
        raise SystemExit("Separate development Telegram approval and disabled reminder delivery required")
    info = config["telegram"]
    _verify_bot(info, config["owner_id"])
    with httpx.Client(timeout=30, trust_env=False,
                      transport=httpx.HTTPTransport(uds=config["n8n_socket"])) as client:
        commands = OrchestrationClient(client, "http://n8n/webhook/m2g-lunar", config["command_key"])
        recurring = config.get("development_recurring") is True
        alerts = (OrchestrationClient(client, "http://n8n/webhook/m2g-lunar", config["tick_key"])
                  if recurring else None)
        app = Application.builder().token(info["token"]).build()
        register_lunar_previews(app, info["owner_id"], commands,
                                recurring=recurring, alert_ticks=alerts)
        app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query"])
