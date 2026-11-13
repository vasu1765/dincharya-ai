"""Explicit configuration for disposable reminder acceptance."""
from dataclasses import dataclass, field
import re


@dataclass(frozen=True)
class AcceptanceConfig:
    token: str = field(repr=False)
    owner_id: int
    database: dict = field(repr=False)


def load_acceptance(env):
    # libpq can inherit service, password-file and connection settings from PG*.
    if any(key.startswith('PG') for key in env):
        raise ValueError('Clear inherited PostgreSQL environment settings first.')
    if any(key.lower() in {'http_proxy', 'https_proxy', 'all_proxy', 'ssl_cert_file', 'ssl_cert_dir'}
           for key in env):
        raise ValueError('Clear inherited HTTP proxy and certificate settings first.')
    if any(key in env for key in (
        'TELEGRAM_BOT_TOKEN', 'TELEGRAM_ALLOWED_USER_ID', 'DINCHARYA_REMINDER_DSN',
        'N8N_WEBHOOK_URL',
    )):
        raise ValueError('Clear regular gateway settings before acceptance.')

    def required(name):
        value = env.get(f'DINCHARYA_TEST_{name}')
        if not value:
            raise ValueError(f'Missing DINCHARYA_TEST_{name}.')
        return value

    token = required('BOT_TOKEN')
    bot_id = required('BOT_ID')
    owner = required('OWNER_ID')
    port = required('PG_PORT')
    if not re.fullmatch(r'[1-9][0-9]{0,18}', bot_id):
        raise ValueError('Provide the numeric ID of the dedicated test bot.')
    if not re.fullmatch(re.escape(bot_id) + r':[A-Za-z0-9_-]+', token):
        raise ValueError('The acceptance token must match the pinned test bot ID.')
    if not re.fullmatch(r'[1-9][0-9]{0,18}', owner) or int(owner) >= 2**63:
        raise ValueError('Provide a valid private Telegram test owner ID.')
    if not re.fullmatch(r'[1-9][0-9]{0,4}', port) or not 1 <= int(port) <= 65535 or port == '5432':
        raise ValueError('Use the disposable database on a dedicated loopback port.')
    database = {
        'hostaddr': '127.0.0.1',
        'port': port,
        'dbname': 'dincharya_app_test',
        'user': 'synthetic_test',
        'passfile': '/dev/null',
        'sslmode': 'disable',
    }
    database['password'] = required('PG_PASSWORD')
    return AcceptanceConfig(token, int(owner), database)


def decision_reply(success, message, decision):
    if success is True:
        return f'Reminder {"scheduled" if decision == "approve" else "proposal rejected"}.'
    if success is False:
        return f'Reminder decision declined. {message}'
    return 'Could not confirm the reminder decision.'
