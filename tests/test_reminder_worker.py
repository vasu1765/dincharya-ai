from datetime import datetime, timezone
import unittest
from unittest.mock import Mock
from dincharya.reminders import Claim, DeliveryReceipt, DeliveryUncertain, NotAccepted, process_batch


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.repository = Mock()
        self.repository.claim.return_value = [Claim(1, 'invented-lease', {'title': 'Synthetic'})]
        self.repository.finish.return_value = True
        self.transport = Mock()
        self.transport.send.return_value = DeliveryReceipt(101, 12)
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
                    self.repository.claim.return_value[0], outcome, self.clock(),
                    **({'receipt': self.transport.send.return_value} if outcome == 'sent' else {}))

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

    def test_receipt_is_passed_only_to_the_single_sent_acknowledgement(self):
        receipt = DeliveryReceipt(101, 12)
        self.transport.send.return_value = receipt
        self.assertEqual(process_batch(self.repository, self.transport, self.clock, 1), 1)
        self.repository.finish.assert_called_once_with(
            self.repository.claim.return_value[0], 'sent', self.clock(), receipt=receipt)
        self.transport.send.assert_called_once()

    def test_receipt_ack_failure_never_replays_send_or_exposes_identifiers(self):
        import traceback
        self.transport.send.return_value = DeliveryReceipt(101, 12)
        for result in (False, RuntimeError('synthetic private receipt storage error')):
            with self.subTest(result_type=type(result).__name__):
                self.repository.finish.reset_mock()
                self.transport.reset_mock()
                self.repository.finish.side_effect = result if isinstance(result, Exception) else None
                self.repository.finish.return_value = result
                with self.assertRaises(DeliveryUncertain) as caught:
                    process_batch(self.repository, self.transport, self.clock, 1)
                self.assertNotIn('synthetic private', ''.join(traceback.format_exception(caught.exception)))
                self.assertNotIn('101', repr(self.transport.send.return_value))
                self.transport.send.assert_called_once()
                self.repository.finish.assert_called_once()

    def test_invalid_transport_receipt_is_quarantined_without_replay(self):
        self.transport.send.return_value = {'message_id': 12, 'chat_id': 101}
        with self.assertRaises(DeliveryUncertain):
            process_batch(self.repository, self.transport, self.clock, 1)
        self.repository.finish.assert_called_once_with(
            self.repository.claim.return_value[0], 'uncertain', self.clock())
        self.transport.send.assert_called_once()

    def test_receipt_rejects_non_integer_zero_and_out_of_range_identifiers(self):
        for chat, message in ((True, 1), (0, 1), (101, False), (101, 0),
                              (101, -1), (2**63, 1), (101, 2**63)):
            with self.subTest(chat=chat, message=message), self.assertRaises(ValueError):
                DeliveryReceipt(chat, message)

    def test_invalid_batch_rejected_before_claim(self):
        for limit in (0, 101, True, None):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                process_batch(self.repository, self.transport, self.clock, limit)
        self.repository.claim.assert_not_called()


if __name__ == '__main__':
    unittest.main()
