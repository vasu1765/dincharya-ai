"""Mocked gateway startup only; requires the optional gateway dependencies."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

AVAILABLE = all(importlib.util.find_spec(name) is not None for name in ('telegram', 'httpx', 'psycopg'))
if AVAILABLE:
    directory = Path(__file__).resolve().parents[1] / 'telegram-gateway'
    sys.path.insert(0, str(directory))
    try:
        spec = importlib.util.spec_from_file_location('reminder_handlers_preflight', directory / 'reminder_handlers.py')
        handlers = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handlers)
    finally:
        sys.path.pop(0)


@unittest.skipUnless(AVAILABLE, 'Optional gateway packages unavailable')
class GatewayPreflightTests(unittest.TestCase):
    def test_missing_receipt_migration_stops_before_handlers_or_polling(self):
        app, connection = Mock(), Mock()
        connection.execute.return_value.fetchone.return_value = (False,)
        with patch('psycopg.connect', return_value=connection):
            with self.assertRaisesRegex(ValueError, 'migrations could not be verified'):
                handlers.register_reminders(app, 'synthetic', 101, database={'dbname': 'dincharya_app_test'})
        sql = connection.execute.call_args.args[0]
        self.assertIn('0004_telegram_receipts.sql', sql)
        self.assertIn('acknowledge_occurrence_reminder', sql)
        self.assertIn("session_user = 'synthetic_test'", sql)
        app.add_handler.assert_not_called()
        app.job_queue.run_repeating.assert_not_called()
        connection.close.assert_called_once()

    def test_regular_opt_in_also_checks_migrations_before_registering_ticks(self):
        app, connection = Mock(), Mock()
        connection.execute.return_value.fetchone.return_value = (True,)
        with patch('psycopg.connect', return_value=connection):
            handlers.register_reminders(app, 'synthetic', 101, dsn='synthetic-dsn')
        sql = connection.execute.call_args.args[0]
        self.assertIn('0004_telegram_receipts.sql', sql)
        self.assertNotIn('session_user', sql)
        self.assertEqual(app.add_handler.call_count, 3)
        app.job_queue.run_repeating.assert_called_once()
        connection.close.assert_called_once()
