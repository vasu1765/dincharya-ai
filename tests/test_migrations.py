"""Offline checks for migration delivery; runtime behavior is tested in disposable PG."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('migration_renderer', ROOT / 'database/migrate.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class MigrationTests(unittest.TestCase):
    def test_changed_migration_changes_immutable_ledger_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '0001_test.sql'
            path.write_text('SELECT 1;\n')
            first = m.render_migrations([path])
            path.write_text('SELECT 2;\n')
            second = m.render_migrations([path])
            self.assertNotEqual(first, second)
            self.assertIn('Migration checksum mismatch', second)
            self.assertIn("current_database()<>'dincharya_app_test'", second)
            self.assertLess(second.index('pg_advisory_xact_lock'), second.index('SELECT 2;'))
            self.assertTrue(second.endswith('COMMIT;\n'))

    def test_reordered_and_duplicate_versions_fail_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ('0002_test.sql','0001_test.sql','0001_other.sql')]
            for path in paths: path.write_text('SELECT 1;')
            for sequence in (paths[:2], paths[1:]):
                with self.assertRaises(ValueError): m.render_migrations(sequence)

    def test_symlinks_and_unexpected_filenames_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '0001_test.sql'
            path.symlink_to(Path(directory) / 'missing')
            with self.assertRaises(ValueError): m.render_migrations([path])
            with self.assertRaises(ValueError): m.render_migrations([Path(directory) / '.env'])

    def test_repository_migrations_render_without_services_or_private_input(self):
        text = m.render_migrations([ROOT / 'database/migrations' / name for name in
            ('0001_gregorian_occurrences.sql','0002_occurrence_reminders.sql',
             '0003_managed_legacy_boundary.sql','0004_telegram_receipts.sql',
             '0005_synthetic_reconciliation.sql')])
        self.assertIn('CREATE FUNCTION public.propose_gregorian_change', text)
        self.assertIn('CREATE FUNCTION public.claim_occurrence_reminders', text)
        self.assertIn('CREATE TRIGGER guard_legacy_managed_request', text)
        self.assertIn('CREATE FUNCTION public.acknowledge_occurrence_reminder', text)
        self.assertIn('CREATE FUNCTION reconcile_api.record_confirmed_delivered', text)
        self.assertNotIn('CREATE DATABASE', text)


if __name__ == '__main__':
    unittest.main()
