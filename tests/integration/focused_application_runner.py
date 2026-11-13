"""Run only named SQL cases in disposable, network-disabled PostgreSQL; no n8n."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runner import ROOT, ENDPOINT, IMAGES, Failure, client_environment, require, validate_daemon
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from database.migrate import render_migrations
from source_sync import validate_schema
from legacy_boundary_checks import concurrent_legacy_boundary
from adversarial_checks import adversarial_decisions, concurrent_receipt

MIGRATIONS = ('0001_gregorian_occurrences.sql', '0002_occurrence_reminders.sql',
              '0003_managed_legacy_boundary.sql', '0004_telegram_receipts.sql')
CASES = ('legacy_coexistence.sql', 'legacy_managed_boundary.sql', 'reminder_recovery.sql',
         'legacy-concurrency', 'gregorian_adversarial.sql', 'telegram_receipts.sql',
         'adversarial-concurrency', 'receipt-concurrency')


def execute(baseline, expected_daemon, cases):
    require(baseline.is_file() and not baseline.is_symlink(), 'Explicit regular schema file required')
    require(bool(cases) and all(case in CASES for case in cases), 'Unknown focused test case')
    require(len(cases) == len(set(cases)), 'Duplicate focused cases are not allowed')
    require(not any(case.endswith('-concurrency') for case in cases[:-1]), 'Run the committing concurrency case last')
    with tempfile.TemporaryDirectory(prefix='dincharya-focused-sql-') as directory:
        env = client_environment(os.environ, directory)
        docker = ['docker', '--config', directory, '--host', ENDPOINT]
        container = None
        original_ids = None

        def command(args, data=None, *, timeout=90):
            try:
                result = subprocess.run(docker + args, input=data, text=True, capture_output=True,
                                        env=env, timeout=timeout)
            except subprocess.TimeoutExpired:
                raise Failure('Focused test command timed out; private output suppressed') from None
            require(result.returncode == 0, 'Focused test command failed; private output suppressed')
            return result.stdout.strip()

        def sql(statement):
            return command(['exec', '-i', container, 'psql', '-XAt', '-v', 'ON_ERROR_STOP=1',
                            '-U', 'synthetic_test', '-d', 'dincharya_app_test'], statement)

        try:
            validate_daemon(json.loads(command(['info', '--format', '{{json .}}'])), expected_daemon)
            image = IMAGES['postgres-test']
            require(command(['image', 'inspect', '--format', '{{.Id}}', image]) == image,
                    'Pinned local image unavailable')
            original_ids = set(command(['ps', '-q', '--no-trunc']).splitlines())
            env['POSTGRES_PASSWORD'] = secrets.token_hex(24)
            container = command(['run', '-d', '--pull=never', '--name', Path(directory).name,
                '--network', 'none', '--read-only', '--security-opt', 'no-new-privileges',
                '--memory', '512m', '--tmpfs', '/var/lib/postgresql/data:size=256m',
                '--tmpfs', '/var/run/postgresql:size=16m', '--tmpfs', '/tmp:size=32m',
                '-e', 'POSTGRES_PASSWORD', '-e', 'POSTGRES_USER=synthetic_test',
                '-e', 'POSTGRES_DB=dincharya_app_test', image])
            env.pop('POSTGRES_PASSWORD', None)
            info = json.loads(command(['inspect', container]))[0]
            host = info['HostConfig']
            require(info['Image'] == image and host['ReadonlyRootfs'] and not host['Privileged']
                    and host['NetworkMode'] == 'none' and not host['PortBindings']
                    and all(m['Type'] == 'tmpfs' for m in info['Mounts']), 'Isolation mismatch')
            for _ in range(30):
                ready = subprocess.run(docker + ['exec', container, 'pg_isready', '-h', '127.0.0.1',
                    '-U', 'synthetic_test', '-d', 'dincharya_app_test'], env=env, capture_output=True,
                    timeout=10)
                if ready.returncode == 0:
                    break
                time.sleep(1)
            require(sql("SELECT current_database(),session_user,current_setting('server_version_num')::int/10000")
                    == 'dincharya_app_test|synthetic_test|17', 'Test database identity mismatch')
            require(sql("SELECT count(*) FROM pg_tables WHERE schemaname='public'") == '0', 'Database not empty')
            raw = baseline.read_bytes()
            sql(validate_schema(raw).decode('utf-8'))
            signatures = (
                'public.process_schedule_decision(bigint,bigint,text,boolean)',
                'public.create_schedule_change_proposal(text,bigint,bigint,text,time without time zone,time without time zone)',
            )
            bodies = {sig: sql("SELECT prosrc FROM pg_proc WHERE oid='" + sig + "'::regprocedure") for sig in signatures}
            def properties(sig):
                return sql("SELECT proowner,proacl,prosecdef,proconfig,provolatile,proparallel "
                           "FROM pg_proc WHERE oid='" + sig + "'::regprocedure")
            attributes = {sig: properties(sig) for sig in signatures}
            sql(render_migrations([ROOT / 'database/migrations' / name for name in MIGRATIONS[:-1]]))
            old_ack = sql("SELECT prosrc FROM pg_proc WHERE oid='public.finish_occurrence_reminder(bigint,uuid,text,timestamp with time zone)'::regprocedure")
            historical_event = None
            if any('receipt' in case for case in cases):
                historical_event = int(sql("INSERT INTO public.schedule_events(title,start_time,recurrence,event_date) "
                    "VALUES('Synthetic historical receipt','08:00','once','2000-01-01') RETURNING id").splitlines()[0])
                sql(f"INSERT INTO public.reminder_deliveries(event_id,occurrence_date,status) VALUES({historical_event},'2000-01-01','sent')")
                old_history = sql(f'SELECT to_jsonb(d) FROM public.reminder_deliveries d WHERE event_id={historical_event}')
            sql(render_migrations([ROOT / 'database/migrations' / name for name in MIGRATIONS]))
            require(old_ack == sql("SELECT prosrc FROM pg_proc WHERE oid='public.finish_occurrence_reminder(bigint,uuid,text,timestamp with time zone)'::regprocedure"),
                    'Original acknowledgement API changed')
            if historical_event is not None:
                require(old_history == sql("SELECT to_jsonb(d)-'telegram_chat_id'-'telegram_message_id' "
                    f'FROM public.reminder_deliveries d WHERE event_id={historical_event}'), 'Historical ledger changed on upgrade')
                require(sql(f'SELECT telegram_chat_id IS NULL AND telegram_message_id IS NULL FROM public.reminder_deliveries WHERE event_id={historical_event}') == 't',
                        'Historical receipt invented')
                sql(f'DELETE FROM public.reminder_deliveries WHERE event_id={historical_event}; '
                    f'DELETE FROM public.recurrence_rules WHERE event_id={historical_event}; '
                    f'DELETE FROM public.schedule_events WHERE id={historical_event}')
                print('PASS incremental receipt upgrade preserves historical row and nullable IDs', flush=True)
            require(sql('SELECT version FROM public.application_migration_ledger ORDER BY version').splitlines()
                    == list(MIGRATIONS), 'Migration ledger mismatch')
            for sig in signatures:
                require(bodies[sig] in sql("SELECT prosrc FROM pg_proc WHERE oid='" + sig + "'::regprocedure")
                        and properties(sig) == attributes[sig], 'Legacy body or function properties changed')
            require(baseline.read_bytes() == raw, 'Authorized schema input changed')
            print('PASS pinned daemon/image, no-network isolation, fresh DB, four migrations and preserved legacy contracts', flush=True)
            for case in cases:
                print('RUN focused case: ' + case, flush=True)
                if case == 'legacy-concurrency':
                    concurrent_legacy_boundary(sql)
                elif case == 'adversarial-concurrency':
                    adversarial_decisions(sql)
                elif case == 'receipt-concurrency':
                    concurrent_receipt(sql)
                else:
                    require(sql((ROOT / 'tests/sql' / case).read_text()).endswith('ROLLBACK'),
                            'Focused SQL did not roll back')
                    print('PASS ' + case, flush=True)
        finally:
            env.pop('POSTGRES_PASSWORD', None)
            if container:
                command(['rm', '-f', '-v', container])
                require(container not in command(['ps', '-aq', '--no-trunc']).splitlines(), 'Cleanup incomplete')
                require(set(command(['ps', '-q', '--no-trunc']).splitlines()) == original_ids,
                        'Original running container IDs changed')
                print('PASS disposable teardown; original running container IDs unchanged', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--expected-daemon-id', required=True)
    parser.add_argument('--case', action='append', choices=CASES, required=True)
    parser.add_argument('--execute-approved', action='store_true')
    args = parser.parse_args()
    try:
        require(args.execute_approved, 'Explicit isolated execution approval required')
        execute(args.baseline, args.expected_daemon_id, args.case)
    except (Failure, AssertionError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, ValueError):
        print('Focused acceptance failed; private output suppressed; inspect the last case label', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
