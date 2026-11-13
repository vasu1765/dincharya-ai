"""Explicit live acceptance entry; never selected by the regular gateway mode."""
import httpx
import os
import logging
from urllib.parse import quote
from telegram.ext import Application
from dincharya.lunar_runtime import read_private,validate_test_bot
from lunar_handlers import OrchestrationClient,register_lunar


def run_live(path):
    if any(k.startswith('PG') or k.lower() in ('http_proxy','https_proxy','all_proxy','ssl_cert_file','ssl_cert_dir') for k in os.environ):
        raise SystemExit('Clear inherited PostgreSQL/proxy/certificate settings')
    config=read_private(path)
    if config.get('live_gateway_approved') is not True or config.get('delivery_enabled') is not True:
        raise SystemExit('Explicit private Telegram acceptance approval is required')
    info=config['telegram'];token=info['token']
    validate_test_bot(info,config['owner_id'])
    class PrivateFormatter(logging.Formatter):
        def format(self,record):
            return super().format(record).replace(token,'[redacted]').replace(quote(token,safe=''),'[redacted]')
    logging.basicConfig(level=logging.WARNING,force=True)
    for handler in logging.getLogger().handlers:handler.setFormatter(PrivateFormatter())
    for name in ('telegram','httpx','httpcore'):logging.getLogger(name).setLevel(logging.CRITICAL)
    client=httpx.Client(timeout=30,trust_env=False,transport=httpx.HTTPTransport(uds=config['n8n_socket']))
    with httpx.Client(timeout=10,trust_env=False) as identity_client:
        response=identity_client.post('https://api.telegram.org/bot'+token+'/getMe');body=response.json()
        if response.status_code!=200 or body.get('ok') is not True or body.get('result',{}).get('username')!='dincharya_acceptance_test_bot':
            raise SystemExit('Dedicated test bot verification failed')
    app=Application.builder().token(token).build()
    register_lunar(app,info['owner_id'],OrchestrationClient(client,'http://n8n/webhook/m2g-lunar',config['command_key']),
                   OrchestrationClient(client,'http://n8n/webhook/m2g-lunar',config['tick_key']))
    try:app.run_polling(drop_pending_updates=False)
    finally:client.close()
