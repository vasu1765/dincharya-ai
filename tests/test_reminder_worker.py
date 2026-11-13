from datetime import datetime, timezone
import unittest
from unittest.mock import Mock
from dincharya.reminders import Claim, DeliveryUncertain, NotAccepted, process_batch


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.repository = Mock()
        self.repository.claim.return_value = [Claim(1, 'invented-lease', {'title': 'Synthetic'})]
        self.repository.finish.return_value = True
        self.transport = Mock()
        self.clock = lambda: datetime(2032, 1, 1, tzinfo=timezone.utc)

    def test_confirmed_acceptance_is_acknowledged_once(self):
        self.assertEqual(process_batch(self.repository, self.transport, self.clock), 1)
        self.transport.send.assert_called_once()
        self.assertEqual(self.repository.finish.call_args.args[1], 'sent')

    def test_only_definite_rejection_is_retryable(self):
        self.transport.send.side_effect = NotAccepted()
        self.assertEqual(process_batch(self.repository, self.transport, self.clock), 0)
        self.assertEqual(self.repository.finish.call_args.args[1], 'not_accepted')
        self.transport.send.assert_called_once()

    def test_unknown_error_is_quarantined_without_transport_replay_or_payload_leak(self):
        self.transport.send.side_effect = TimeoutError('private transport details')
        with self.assertRaises(DeliveryUncertain) as error:
            process_batch(self.repository, self.transport, self.clock)
        self.assertNotIn('private', str(error.exception))
        self.assertEqual(self.repository.finish.call_args.args[1], 'uncertain')
        self.transport.send.assert_called_once()

    def test_acknowledgement_lease_loss_does_not_resend(self):
        self.repository.finish.return_value = False
        with self.assertRaises(DeliveryUncertain): process_batch(self.repository, self.transport, self.clock)
        self.transport.send.assert_called_once()

    def test_database_finish_failure_is_safe_uncertainty_for_each_transport_outcome(self):
        import traceback
        for transport_error, outcome in ((None, 'sent'), (NotAccepted(), 'not_accepted'),
                                          (TimeoutError('synthetic transport detail'), 'uncertain')):
            with self.subTest(outcome=outcome):
                self.repository.reset_mock()
                self.transport.reset_mock()
                self.transport.send.side_effect = transport_error
                self.repository.finish.side_effect = RuntimeError('synthetic private database detail')
                with self.assertRaises(DeliveryUncertain) as caught:
                    process_batch(self.repository, self.transport, self.clock, 1)
                formatted = ''.join(traceback.format_exception(caught.exception))
                self.assertNotIn('synthetic private database detail', formatted)
                self.assertNotIn('synthetic transport detail', formatted)
                self.transport.send.assert_called_once()
                self.repository.finish.assert_called_once_with(
                    self.repository.claim.return_value[0], outcome, self.clock())

    def test_failed_acknowledgement_aborts_batch_before_second_send(self):
        first = self.repository.claim.return_value[0]
        second = Claim(2, 'second-synthetic-lease', {'title': 'Other synthetic'})
        self.repository.claim.return_value = [first, second]
        for result in (False, RuntimeError('synthetic database detail')):
            with self.subTest(result_type=type(result).__name__):
                self.transport.reset_mock()
                self.repository.finish.reset_mock()
                self.repository.finish.side_effect = result if isinstance(result, Exception) else None
                self.repository.finish.return_value = result
                with self.assertRaises(DeliveryUncertain):
                    process_batch(self.repository, self.transport, self.clock, 2)
                self.transport.send.assert_called_once_with(first.payload)
                self.repository.finish.assert_called_once()

    def test_no_due_work_makes_no_transport_call(self):
        self.repository.claim.return_value = []
        self.assertEqual(process_batch(self.repository, self.transport, self.clock), 0)
        self.transport.send.assert_not_called()

    def test_invalid_batch_rejected_before_claim(self):
        for limit in (0, 101, True, None):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                process_batch(self.repository, self.transport, self.clock, limit)
        self.repository.claim.assert_not_called()


if __name__ == '__main__':
    unittest.main()
