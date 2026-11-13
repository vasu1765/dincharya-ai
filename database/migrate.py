"""Render a checksummed, transactional psql migration script for the isolated test DB.

This module never connects to a database. Production application is deliberately unsupported.
"""
import hashlib
from pathlib import Path
import re


def render_migrations(paths):
    entries = []
    names = set()
    for path in paths:
        path = Path(path)
        if not re.fullmatch(r'[0-9]{4}_[a-z0-9_]+\.sql', path.name) or path.is_symlink():
            raise ValueError('Invalid migration source')
        if path.name[:4] in names:
            raise ValueError('Duplicate migration version')
        names.add(path.name[:4])
        raw = path.read_bytes()
        entries.append((path.name, hashlib.sha256(raw).hexdigest(), raw.decode('utf-8')))
    if [name for name, _, _ in entries] != sorted(name for name, _, _ in entries):
        raise ValueError('Migrations must be explicitly ordered')
    script = ["\\set ON_ERROR_STOP on", 'BEGIN;',
              "DO $$ BEGIN IF current_database()<>'dincharya_app_test' THEN RAISE EXCEPTION 'Isolated application database required'; END IF; END $$;",
              'SELECT pg_advisory_xact_lock(20261112,2);',
              'CREATE TABLE IF NOT EXISTS public.application_migration_ledger '
              '(version text PRIMARY KEY, checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now());']
    for name, checksum, sql in entries:
        script += [f"SELECT EXISTS(SELECT FROM public.application_migration_ledger WHERE version='{name}') AS applied \\gset",
                   '\\if :applied',
                   f"DO $$ BEGIN IF (SELECT checksum FROM public.application_migration_ledger WHERE version='{name}') <> '{checksum}' "
                   "THEN RAISE EXCEPTION 'Migration checksum mismatch'; END IF; END $$;",
                   '\\else', sql,
                   f"INSERT INTO public.application_migration_ledger(version,checksum) VALUES('{name}','{checksum}');",
                   '\\endif']
    script += ['COMMIT;']
    return '\n'.join(script) + '\n'
