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
