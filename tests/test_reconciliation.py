from dataclasses import replace
from uuid import UUID
import traceback
import unittest
from unittest.mock import MagicMock, Mock

from dincharya.reconciliation import ConfirmedDelivery, OperatorReconciliation
from dincharya.reminders import Claim, DeliveryReceipt
from dincharya.reminder_adapters import PostgresReminders


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.session = self.connection.__enter__.return_value
        self.connect = Mock(return_value=self.connection)
        self.api = OperatorReconciliation(self.connect)
        self.command = ConfirmedDelivery(UUID(int=1),7,'a'*64,DeliveryReceipt(101,12),
            UUID(int=2),'Synthetic verified delivery',UUID(int=3),True)

    def test_explicit_authorization_and_evidence_are_required_before_connecting(self):
        for change in ({'confirmed':False},{'confirmed':1},{'reason':''},{'reason':'bad\nreason'},
                       {'observation_version':'bad'},{'delivery_id':True},{'action_id':'not-a-uuid'},
                       {'evidence_ref':None}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                replace(self.command,**change)
        with self.assertRaises(ValueError):
            self.api.record_confirmed({'actor_id':101})
        self.connect.assert_not_called()

    def test_actor_is_absent_from_request_and_private_proof_is_not_in_repr(self):
        self.assertFalse({'actor_id','operator_id','role_name'} & set(vars(self.command)))
        self.assertNotIn('101',repr(self.command))
        self.assertNotIn('Synthetic verified',repr(self.command))

    def test_single_parameterized_call_reports_recorded_or_replayed_result(self):
        for row in ((True,False,'recorded'),(True,True,'replayed'),(False,False,'stale_observation')):
            with self.subTest(row=row):
                self.session.execute.reset_mock()
                self.session.execute.return_value.fetchone.return_value=row
                result=self.api.record_confirmed(self.command)
                self.assertEqual((result.success,result.replayed,result.code),row)
                self.session.execute.assert_called_once()
                statement,params=self.session.execute.call_args.args
                self.assertEqual(len(params),9)
                self.assertNotIn(self.command.reason,statement)
                self.assertNotIn('SET ROLE',statement)
                self.assertIn('reconcile_api.record_confirmed_delivered',statement)

    def test_unknown_commit_result_is_sanitized_and_never_automatically_retried(self):
        self.session.execute.return_value.fetchone.return_value=(True,False,'recorded')
        self.connection.__exit__.side_effect=RuntimeError('private synthetic evidence detail')
        with self.assertRaisesRegex(RuntimeError,'replay the same action ID') as caught:
            self.api.record_confirmed(self.command)
        self.assertNotIn('private synthetic',''.join(traceback.format_exception(caught.exception)))
        self.connect.assert_called_once()
        self.session.execute.assert_called_once()

    def test_inspection_is_read_only_and_invalid_bounds_do_not_connect(self):
        self.session.execute.return_value.fetchall.return_value=[]
        self.assertEqual(self.api.inspect(after_id=4,limit=1),[])
        self.assertEqual(self.session.execute.call_args_list[0].args,('SET TRANSACTION READ ONLY',))
        self.assertEqual(self.session.execute.call_args_list[1].args,
                         ('SELECT * FROM reconcile_api.inspect_uncertain(%s,%s)',(4,1)))
        self.connect.reset_mock()
        for args in ({'after_id':-1},{'after_id':2**63},{'limit':101},{'limit':True}):
            with self.subTest(args=args),self.assertRaises(ValueError):
                self.api.inspect(**args)
        self.connect.assert_not_called()

    def test_restricted_worker_uses_only_lease_wrappers(self):
        worker=PostgresReminders(self.connect,restricted_worker=True)
        self.session.execute.return_value.fetchall.return_value=[]
        self.assertEqual(worker.claim(None,1),[])
        self.assertIn('reminder_worker_api.claim_occurrence_reminders',self.session.execute.call_args.args[0])
        self.session.execute.return_value.fetchone.return_value=(True,)
        claim=Claim(7,str(UUID(int=4)),{})
        worker.finish(claim,'sent',None,receipt=DeliveryReceipt(101,12))
        self.assertIn('reminder_worker_api.acknowledge_occurrence_reminder',self.session.execute.call_args.args[0])
        worker.finish(claim,'uncertain',None)
        self.assertIn('reminder_worker_api.finish_occurrence_reminder',self.session.execute.call_args.args[0])
        with self.assertRaises(ValueError):
            PostgresReminders(self.connect,restricted_worker='untrusted-schema')
