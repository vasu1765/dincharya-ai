"""Fail-closed tests for missing or malformed external reminder receipts."""
from datetime import datetime, timezone
import unittest
from unittest.mock import Mock

from dincharya.reminders import Claim, DeliveryReceipt, DeliveryUncertain, NotAccepted, process_batch


class ReceiptSafetyTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2032, 1, 2, 3, 4, tzinfo=timezone.utc)
        self.claim = Claim(7, "synthetic-lease", {"title": "Synthetic"})
        self.repo = Mock()
        self.repo.claim.return_value = [self.claim]
        self.repo.finish.return_value = True
        self.transport = Mock()

    def test_missing_receipt_is_quarantined_not_sent(self):
        self.transport.send.return_value = None
        with self.assertRaises(DeliveryUncertain):
            process_batch(self.repo, self.transport, lambda: self.now, 1)
        self.repo.finish.assert_called_once_with(self.claim, "uncertain", self.now)
        self.transport.send.assert_called_once_with(self.claim.payload)

    def test_untyped_receipts_are_quarantined_not_sent(self):
        for result in (True, {"chat_id": 101, "message_id": 2}, "ok"):
            with self.subTest(result=result):
                self.repo.reset_mock()
                self.repo.claim.return_value = [self.claim]
                self.repo.finish.return_value = True
                self.transport.send.return_value = result
                with self.assertRaises(DeliveryUncertain):
                    process_batch(self.repo, self.transport, lambda: self.now, 1)
                self.repo.finish.assert_called_once_with(self.claim, "uncertain", self.now)

    def test_valid_receipt_is_acknowledged(self):
        receipt = DeliveryReceipt(101, 2)
        self.transport.send.return_value = receipt
        self.assertEqual(process_batch(self.repo, self.transport, lambda: self.now, 1), 1)
        self.repo.finish.assert_called_once_with(self.claim, "sent", self.now, receipt=receipt)

    def test_definitive_rejection_remains_retryable(self):
        self.transport.send.side_effect = NotAccepted()
        self.assertEqual(process_batch(self.repo, self.transport, lambda: self.now, 1), 0)
        self.repo.finish.assert_called_once_with(self.claim, "not_accepted", self.now)

    def test_acknowledgement_storage_failure_remains_uncertain(self):
        self.transport.send.return_value = DeliveryReceipt(101, 2)
        self.repo.finish.side_effect = RuntimeError("private details")
        with self.assertRaises(DeliveryUncertain) as caught:
            process_batch(self.repo, self.transport, lambda: self.now, 1)
        self.assertNotIn("private details", str(caught.exception))
        self.transport.send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
