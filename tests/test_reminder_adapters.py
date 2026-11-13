from datetime import datetime, timezone
import json
import unittest
from unittest.mock import MagicMock, Mock
from uuid import UUID
from zoneinfo import ZoneInfo

from dincharya.reminder_adapters import PostgresReminders, TelegramReminders, parse_reminder
from dincharya.reminders import NotAccepted, process_batch


class ReminderAdapterTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2032, 1, 2, 3, 4, tzinfo=timezone.utc)
        self.connection = MagicMock()
        self.session = self.connection.__enter__.return_value
        self.cursor = self.session.execute.return_value
        self.repository = PostgresReminders(Mock(return_value=self.connection))
        self.post = Mock()
        self.transport = TelegramReminders(self.post, 'synthetic', 101)
        self.payload = {'title': 'Havan', 'occurrence_date': '2032-01-02',
                        'start_time': '08:34:00', 'timezone': 'Asia/Kolkata'}

    def test_proposal_is_separate_from_owner_decision(self):
        local_now = self.now.astimezone(ZoneInfo('Asia/Kolkata'))
        when, title = parse_reminder(['2032-01-02', '08:35', 'Havan'], local_now)
        self.cursor.fetchone.return_value = (7,)
        self.assertEqual(self.repository.propose(101, when, title), 7)
        query, (data, owner_id) = self.session.execute.call_args.args
        self.assertIn('propose_gregorian_change', query)
        self.assertEqual(owner_id, 101)
        self.assertEqual(json.loads(data)['recurrence_rule']['frequency'], 'once')
        self.cursor.fetchone.return_value = (True, 'Approved')
        self.assertEqual(self.repository.decide(101, 7, 'approve'), (True, 'Approved'))
        query, params = self.session.execute.call_args.args
        self.assertIn('decide_gregorian_change', query)
        self.assertEqual(params, (7, 101, 'approve'))

    def test_send_follows_committed_claim_and_acknowledges_by_worker_token(self):
        worker = UUID(int=1)
        self.cursor.fetchall.return_value = [(5, worker, self.payload)]
        self.cursor.fetchone.return_value = (True,)
        self.post.return_value.status_code = 200
        self.post.return_value.json.return_value = {'ok': True, 'result': {'message_id': 12}}

        def check_commit(*args, **kwargs):
            self.connection.__exit__.assert_called_once_with(None, None, None)
            return self.post.return_value

        self.post.side_effect = check_commit
        self.assertEqual(process_batch(self.repository, self.transport, lambda: self.now, 1), 1)
        self.assertEqual(self.post.call_args.kwargs['json']['chat_id'], 101)
        self.assertIn('Havan', self.post.call_args.kwargs['json']['text'])
        self.assertEqual(self.session.execute.call_args.args[1], (5, worker, 'sent', self.now))
        self.assertEqual(self.connection.__exit__.call_count, 2)

    def test_telegram_errors_distinguish_rejection_from_uncertainty(self):
        response = self.post.return_value
        response.status_code = 429
        response.json.return_value = {'ok': False, 'error_code': 429}
        with self.assertRaises(NotAccepted):
            self.transport.send(self.payload)
        response.status_code = 502
        response.json.return_value = {'ok': False, 'error_code': 502}
        with self.assertRaisesRegex(RuntimeError, 'acknowledgement unavailable'):
            self.transport.send(self.payload)
        self.post.side_effect = TimeoutError('private URL')
        with self.assertRaisesRegex(RuntimeError, '^Telegram acknowledgement unavailable$'):
            self.transport.send(self.payload)

    def test_parser_rejects_past_and_noncanonical_times(self):
        for date, time in [('2032-01-02', '03:03'), ('2032-1-02', '03:06'), ('2032-02-30', '03:06')]:
            with self.subTest(date=date, time=time), self.assertRaises(ValueError):
                parse_reminder([date, time, 'Havan'], self.now)
