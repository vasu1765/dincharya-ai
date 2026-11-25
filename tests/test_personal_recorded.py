import unittest
from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

from dincharya.personal_recorded import PersonalReview, Recorder, dispatch_recorded
from dincharya.personal_service import deliver_due


class PersonalRecordingTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2027, 5, 5, 2, tzinfo=timezone.utc)
        self.db = Mock(autocommit=True)
        self.row = self.db.execute.return_value.fetchone
        self.row.side_effect = [PersonalReview.database_identity, (True,)]
        self.record = Recorder(903, 904)
        self.lookup = Mock(return_value="Delhi · तिथि · IST")
        self.ui = PersonalReview(self.db, "a"*40, 903, 904, self.record, self.lookup)
        self.request = {"update_id":1, "message":{"date":int(self.now.timestamp()),
                         "from":{"id":903,"is_bot":False},"chat":{"id":903,"type":"private"}}}

    def submit(self, text):
        self.request["message"]["text"] = text
        return dispatch_recorded(self.ui, self.request, self.now)

    def test_cancel_requires_separate_preview(self):
        token = uuid4()
        self.row.side_effect = [(token, uuid4(), "Practice"), (True,)]
        self.assertEqual(self.submit("/cancel "+str(uuid4())), "preview")
        self.assertIn("Cancel future occurrences", self.record.messages[1]["text"])
        self.assertEqual(self.record.calls, ["sendMessage"])
        self.assertFalse(any("ui_decide" in c.args[0] for c in self.db.execute.call_args_list))

    def test_modify_uses_target_bound_draft(self):
        target = uuid4()
        self.row.side_effect = [(uuid4(), uuid4(), "Original"), (True,)]
        self.assertEqual(self.submit(f"/modify {target} Schedule Practice on 2027-05-06 at 07:00"), "preview")
        self.assertIn("Replace Original", self.record.messages[1]["text"])
        self.assertTrue(any("ui_change_draft" in c.args[0] and c.args[1][3] == target
                            for c in self.db.execute.call_args_list if len(c.args)>1))

    def test_foreign_identity_cannot_query(self):
        self.request["message"]["from"]["id"] = 905
        self.assertEqual(self.submit("/rules"),"denied")
        self.assertEqual(self.record.calls, [])

    def test_change_target_cannot_be_injected(self):
        self.request["change_target"] = str(uuid4())
        self.assertEqual(self.submit("Schedule Practice"),"denied")

    def test_detailed_query_has_no_draft(self):
        self.row.side_effect = [(uuid4(),),(True,)]
        self.assertIn("Delhi",self.submit("/details tithi on 2023-12-06"))
        self.lookup.assert_called_once_with("tithi on 2023-12-06",True)
        self.assertFalse(any("ui_draft" in c.args[0] for c in self.db.execute.call_args_list))

    def test_restarted_recorder_uses_shared_allocator(self):
        counter = iter([41,42])
        body = {"chat_id":903,"text":"preview"}
        for expected in (41,42):
            recorder = Recorder(903,904,lambda:next(counter))
            self.assertEqual(recorder("sendMessage",body)["result"]["message_id"],expected)
        self.assertEqual(recorder("editMessageText",{**body,"message_id":41})["result"]["message_id"],41)

    def test_mismatched_worker_receipt_quarantines(self):
        slot = (1,uuid4(),903,"Practice",self.now)
        self.row.side_effect = [slot,(True,)]
        with self.assertRaises(RuntimeError):
            deliver_due(self.db,lambda m,b:{"ok":True,"result":{"from":{} }},903,904)
        self.assertEqual(self.db.execute.call_args.args[1],(1,slot[1],"uncertain",None,None))

    def test_worker_paired_receipt(self):
        slot = (1,uuid4(),903,"Practice",self.now)
        self.row.side_effect = [slot,(True,)]
        deliver_due(self.db,self.record,903,904)
        self.assertEqual(self.db.execute.call_args.args[1],(1,slot[1],"sent",903,1))


class ObserverTests(unittest.TestCase):
    def test_quarantine_or_lost_ownership_blocks_readiness(self):
        from dincharya.personal_health import summarize
        for flags in [(True,False,True,0,0,0,0),(True,True,True,0,1,0,0),(True,True,True,0,0,1,0)]:
            self.assertFalse(summarize(flags)['ready'])
        self.assertTrue(summarize((True,True,True,0,0,0,0))['ready'])
