"""Install the explicitly authorized schema and test migrations only in disposable PostgreSQL."""
import argparse
import importlib.util
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runner
sys.path.insert(0, str(runner.ROOT / "scripts"))
from source_sync import validate_schema

spec = importlib.util.spec_from_file_location('migration_renderer', runner.ROOT / 'database/migrate.py')
migrations = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migrations)


class ApplicationRunner(runner.Runner):
    baseline_path = None

    def psql(self, text):
        return self.compose('exec', '-T', 'postgres-test', 'psql', '-X', '-v', 'ON_ERROR_STOP=1',
                            '-U', 'synthetic_test', '-d', 'dincharya_app_test', data=text, timeout=90)

    def tests(self):
        runner.require(self.sql("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' "
                      "AND table_name<>'synthetic_events'", 'dincharya_app_test') == '0',
                       'Application test database is not fresh')
        baseline = self.baseline_path.read_bytes()
        # Inspect this exact authorized file only. Schema installation is isolated;
        # no rows, credentials, role/DB lifecycle, includes or program execution allowed.
        decoded = validate_schema(baseline).decode('utf-8')
        self.psql(decoded)
        paths = [runner.ROOT / 'database/migrations' / name for name in
                 ('0001_gregorian_occurrences.sql', '0002_occurrence_reminders.sql')]
        script = migrations.render_migrations(paths)
        self.psql(script)
        self.psql(script)  # Repeat is a checked no-op, not a baseline replay.
        # An installed migration with a different checksum must fail closed.
        name = paths[0].name
        original = self.sql("SELECT checksum FROM public.application_migration_ledger WHERE version='" + name + "'",
                            'dincharya_app_test')
        self.sql("UPDATE public.application_migration_ledger SET checksum='synthetic-mismatch' WHERE version='" + name + "'",
                 'dincharya_app_test')
        failed = False
        try:
            self.psql(script)
        except runner.Failure:
            failed = True
        runner.require(failed, 'Changed migration checksum was accepted')
        self.sql("UPDATE public.application_migration_ledger SET checksum='" + original + "' WHERE version='" + name + "'",
                 'dincharya_app_test')
        for name in ('gregorian.sql', 'reminders.sql'):
            self.psql((runner.ROOT / 'tests/sql' / name).read_text())
            print('Isolated application assertions passed: ' + name, flush=True)
        self.concurrent_tests()
        runner.require(self.baseline_path.read_bytes() == baseline, 'Authorized schema changed during testing')
        print('Reviewed schema loaded unchanged; checksummed migrations and application tests passed', flush=True)

    def concurrent_tests(self):
        def query(text):
            return self.sql(text, 'dincharya_app_test')
        data = "jsonb_build_object('title','Synthetic concurrent','start_time'," \
               "((now()-interval '1 minute') AT TIME ZONE 'Asia/Kolkata')::time," \
               "'timezone','Asia/Kolkata','recurrence_rule',jsonb_build_object('calendar_system','gregorian'," \
               "'frequency','once','interval_count',1,'start_date'," \
               "((now()-interval '1 minute') AT TIME ZONE 'Asia/Kolkata')::date))"
        request = str(int(query("SELECT public.propose_gregorian_change('add','series',NULL,NULL," + data + ',101)')))
        decision = "SELECT success::text FROM public.decide_gregorian_change(" + request + ",101,'approve')"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(query, [decision, decision]))
        runner.require(sorted(results) == ['false', 'true'], 'Concurrent decisions were not serialized')
        claim = 'SELECT delivery_id FROM public.claim_occurrence_reminders(now(),1)'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(query, [claim, claim]))
        runner.require(sum(bool(value) for value in results) == 1, 'Concurrent workers claimed duplicate delivery')
        result = query("SELECT public.finish_occurrence_reminder(id,worker_token,'sent',now()) "
                       "FROM public.reminder_deliveries WHERE status='sending' AND managed_by='m2e'")
        runner.require(result == 't', 'Concurrent test acknowledgement failed')
        print('Concurrent approval replay and competing reminder claims passed', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--expected-daemon-id', required=True)
    parser.add_argument('--execute-approved', action='store_true')
    args = parser.parse_args()
    runner.require(args.execute_approved, 'Explicit isolated execution approval required')
    runner.require(args.baseline.is_file() and not args.baseline.is_symlink(), 'Authorized schema must be a regular file')
    ApplicationRunner.baseline_path = args.baseline
    runner.Runner = ApplicationRunner
    try:
        runner.execute(args.expected_daemon_id)
    except runner.Failure as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
