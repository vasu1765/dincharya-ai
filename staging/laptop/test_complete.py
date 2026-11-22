import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from complete import evidence,FIRST,SECOND,LOST,SILENT
from service import Recorder


class IntegratedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.due={FIRST:100,LOST:160,SECOND:280}
        self.slots=[[FIRST,'sent',1,101,1,100],[LOST,'uncertain',1,None,None,160],
                    [SECOND,'sent',1,101,3,280]]
        self.attempts=[[1,0,FIRST,101],[2,1,LOST,161],[3,0,SECOND,292]]

    def test_staging_recorder_persists_attempt_identity_on_lost_reply(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'DINCHARYA_STAGE1_COMPLETE':'1'}):
            path=Path(tmp)/'attempts.db'
            for title in self.due:
                with patch('service.time.time',return_value=self.due[title]+1):
                    if title==LOST:
                        with self.assertRaises(TimeoutError):
                            Recorder(path).send({'title':title})
                    else:
                        Recorder(path).send({'title':title})
            with sqlite3.connect(path) as db:
                rows=db.execute('SELECT a.id,a.uncertain,o.title,o.utc FROM attempts a LEFT JOIN observed o USING(id)').fetchall()
            evidence(self.slots,rows,self.due,set(self.due))

    def test_bad_receipt_or_unexpected_attempt_fails(self):
        for fields in ((0,3,202),(0,4,3),(1,2,2),(1,4,2),(2,5,279)):
            rows=[r[:] for r in self.slots]
            i,j,value=fields
            rows[i][j]=value
            with self.subTest(fields=fields),self.assertRaises(RuntimeError):
                evidence(rows,self.attempts,self.due,set(self.due))
        for extra in ([4,0,SILENT,101],[4,1,LOST,300]):
            with self.assertRaises(RuntimeError):
                evidence(self.slots,self.attempts+[extra],self.due,set(self.due))

    def test_due_window_and_pending_outage(self):
        self.slots[2]=[SECOND,'pending',0,None,None,280]
        evidence(self.slots,self.attempts[:2],self.due,{FIRST,LOST})
        self.attempts[0][-1]=99
        with self.assertRaises(RuntimeError):
            evidence(self.slots,self.attempts[:2],self.due,{FIRST,LOST})
