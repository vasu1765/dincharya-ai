#!/usr/bin/env python3
"""Capture dedicated test credentials locally without echo or command arguments."""
import getpass
import json
import os
from pathlib import Path
import re
import tempfile


def main():
    if not os.isatty(0):
        raise SystemExit('Run interactively in your normal WSL terminal.')
    token = getpass.getpass('Replacement dedicated test-bot token (hidden): ')
    owner = getpass.getpass('Private test owner numeric ID (hidden): ')
    if not re.fullmatch(r'[1-9][0-9]{0,18}:[A-Za-z0-9_-]+', token):
        raise SystemExit('Invalid token format; nothing saved.')
    if not re.fullmatch(r'[1-9][0-9]{0,18}', owner) or int(owner) >= 2**63:
        raise SystemExit('Invalid owner ID; nothing saved.')
    os.umask(0o077)
    directory = Path(tempfile.mkdtemp(prefix='dincharya-test-secrets-', dir='/tmp'))
    path = directory / 'credentials.json'
    with path.open('x', encoding='utf-8') as output:
        json.dump({'token': token, 'owner_id': owner,
                   'username': 'dincharya_acceptance_test_bot'}, output)
    print(f'Saved private test credentials to {path}')
    print('No Telegram request made. Keep this file outside Git and remove it after acceptance.')


if __name__ == '__main__':
    main()
