from datetime import date, datetime, timezone
import json
import unittest
from unittest.mock import MagicMock, Mock
from uuid import UUID
from zoneinfo import ZoneInfo

from dincharya.reminder_adapters import PostgresReminders, TelegramReminders, parse_reminder
from dincharya.reminders import Claim, DeliveryUncertain, NotAccepted, process_batch


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
        response.status_code = 403
        response.json.return_value = {'ok': False, 'error_code': 403}
        with self.assertRaises(NotAccepted):
            self.transport.send(self.payload)
        response.status_code = 502
        response.json.return_value = {'ok': False, 'error_code': 502}
        with self.assertRaisesRegex(RuntimeError, 'acknowledgement unavailable'):
            self.transport.send(self.payload)
        self.post.side_effect = TimeoutError('private URL')
        with self.assertRaisesRegex(RuntimeError, '^Telegram acknowledgement unavailable$'):
            self.transport.send(self.payload)

    def test_rate_limit_is_quarantined_instead_of_ignoring_telegram_wait(self):
        # The SQL rejection policy starts at 30s and has no retry_after input.
        # Even a well-formed 429 must not take that ordinary retry path.
        for parameters in ({'retry_after': 3600}, {'retry_after': 1},
                           {'retry_after': 'invalid'}, None):
            with self.subTest(parameters=parameters):
                self.post.reset_mock()
                self.post.return_value.status_code = 429
                self.post.return_value.json.return_value = {
                    'ok': False, 'error_code': 429, 'parameters': parameters,
                }
                repository = Mock()
                claim = Claim(5, 'synthetic-lease', self.payload)
                repository.claim.return_value = [claim]
                repository.finish.return_value = True
                with self.assertRaises(DeliveryUncertain):
                    process_batch(repository, self.transport, lambda: self.now, 1)
                repository.finish.assert_called_once_with(claim, 'uncertain', self.now)
                self.post.assert_called_once()

    def test_confirmed_non_rate_limit_rejections_keep_bounded_retry_policy(self):
        for code in (400, 401, 403, 404):
            with self.subTest(code=code):
                self.post.return_value.status_code = code
                self.post.return_value.json.return_value = {'ok': False, 'error_code': code}
                repository = Mock()
                claim = Claim(5, 'synthetic-lease', self.payload)
                repository.claim.return_value = [claim]
                repository.finish.return_value = True
                self.assertEqual(process_batch(repository, self.transport, lambda: self.now, 1), 0)
                repository.finish.assert_called_once_with(claim, 'not_accepted', self.now)

    def test_parser_rejects_past_and_noncanonical_times(self):
        for date, time in [('2032-01-02', '03:03'), ('2032-1-02', '03:06'), ('2032-02-30', '03:06')]:
            with self.subTest(date=date, time=time), self.assertRaises(ValueError):
                parse_reminder([date, time, 'Havan'], self.now)

    def test_quarantine_inspection_is_bounded_metadata_only_and_does_not_send(self):
        self.cursor.fetchall.return_value = [(8, 5, date(2032, 1, 2), 1, self.now, self.now)]
        page = self.repository.list_quarantined(after_id=7, limit=1)
        self.assertEqual(page[0].delivery_id, 8)
        self.assertEqual(page[0].event_id, 5)
        self.assertEqual(page[0].attempts, 1)
        self.assertEqual(set(vars(page[0])), {
            'delivery_id', 'event_id', 'occurrence_date', 'attempts', 'due_at', 'claimed_at',
        })
        statement, params = self.session.execute.call_args.args
        self.assertTrue(statement.startswith('SELECT id,event_id,occurrence_date,attempts,due_at,claimed_at '))
        self.assertIn("managed_by='m2e' AND status='uncertain' AND id>%s", statement)
        self.assertEqual(params, (7, 1))
        self.session.execute.assert_called_once()
        self.connection.__exit__.assert_called_once_with(None, None, None)
        self.post.assert_not_called()

    def test_quarantine_inspection_rejects_bad_bounds_before_connecting(self):
        for kwargs in ({'limit': 0}, {'limit': 101}, {'limit': True},
                       {'after_id': -1}, {'after_id': 2**63}, {'after_id': False}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.repository.list_quarantined(**kwargs)
        self.repository.connect.assert_not_called()
