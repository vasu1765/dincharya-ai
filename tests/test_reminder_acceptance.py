import importlib.util
from pathlib import Path
import sys
import unittest

PATH = Path(__file__).resolve().parents[1] / 'telegram-gateway' / 'acceptance.py'
SPEC = importlib.util.spec_from_file_location('acceptance', PATH)
acceptance = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = acceptance
SPEC.loader.exec_module(acceptance)


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            'DINCHARYA_TEST_BOT_ID': '101',
            'DINCHARYA_TEST_BOT_TOKEN': '101:invented',
            'DINCHARYA_TEST_OWNER_ID': '201',
            'DINCHARYA_TEST_PG_PORT': '55432',
            'DINCHARYA_TEST_PG_PASSWORD': 'invented',
        }

    def test_database_target_and_owner_are_fixed(self):
        config = acceptance.load_acceptance(self.env)
        self.assertEqual(config.owner_id, 201)
        self.assertEqual(config.database['hostaddr'], '127.0.0.1')
        self.assertEqual(config.database['dbname'], 'dincharya_app_test')
        self.assertEqual(config.database['user'], 'synthetic_test')
        self.assertEqual(config.database['passfile'], '/dev/null')

    def test_rejects_regular_configuration_and_mismatched_test_bot(self):
        for key, value in (
            ('PGSERVICE', 'inherited'),
            ('HTTPS_PROXY', 'inherited'),
            ('TELEGRAM_BOT_TOKEN', 'inherited'),
            ('DINCHARYA_REMINDER_DSN', 'inherited'),
            ('N8N_WEBHOOK_URL', 'inherited'),
            ('DINCHARYA_TEST_BOT_TOKEN', '102:invented'),
            ('DINCHARYA_TEST_PG_PORT', '5432'),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                acceptance.load_acceptance({**self.env, key: value})

    def test_replies_distinguish_approval_rejection_and_declined_decision(self):
        self.assertEqual(acceptance.decision_reply(True, '', 'approve'), 'Reminder scheduled.')
        self.assertEqual(acceptance.decision_reply(True, '', 'reject'), 'Reminder proposal rejected.')
        self.assertEqual(acceptance.decision_reply(False, 'Already decided', 'approve'),
                         'Reminder decision declined. Already decided')
        self.assertEqual(acceptance.decision_reply(None, '', 'approve'),
                         'Could not confirm the reminder decision.')
