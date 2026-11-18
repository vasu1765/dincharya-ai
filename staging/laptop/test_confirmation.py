"""Offline diagnostic contract with a disposable transactional fixture."""
from contextlib import redirect_stdout
from io import StringIO
import json
import sqlite3
import unittest
from uuid import uuid4

from confirmation import FALLBACK,verify_confirmation


class TestConfirmation(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.control=str(uuid4())
        for table in ('events','controls','audit'):
            self.db.execute(f'CREATE TABLE {table}(id TEXT PRIMARY KEY)')
        self.output=StringIO()

    def ledger(self):
        counts=[self.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                for table in ('events','controls','audit')]
        return [*counts,0,0],self.db.execute('SELECT min(id) FROM controls').fetchone()[0]

    def fixture_commit(self):
        with self.db:
            for table in ('events','controls','audit'):
                self.db.execute(f'INSERT OR IGNORE INTO {table} VALUES (?)',(self.control,))
        return dict(messages=[f'Rule approved. ID {self.control}.'],keyboard=None,relay='approved_reply')

    def test_committed_success_and_same_decision(self):
        for _ in range(2):
            with redirect_stdout(self.output):
                verify_confirmation(self.fixture_commit(),self.ledger)
        self.assertEqual(self.ledger(),([1,1,1,0,0],self.control))
        self.assertNotIn(self.control,self.output.getvalue())

    def test_postcommit_reply_failures(self):
        result=self.fixture_commit()
        for change in ({'messages':[]},{'messages':[FALLBACK]}, {'messages':result['messages']*2},
                       {'messages':[f'Rule approved. ID {uuid4()}.']},{'keyboard':{}},
                       {'relay':'unexpected_result'}):
            out=StringIO()
            with self.subTest(fields=tuple(change)),redirect_stdout(out),self.assertRaises(RuntimeError):
                verify_confirmation({**result,**change},self.ledger)
            diagnostic=json.loads(out.getvalue())
            self.assertEqual(diagnostic['events'],1)
            self.assertNotIn(self.control,out.getvalue())
            self.assertNotIn(FALLBACK,out.getvalue())

    def test_positive_reply_requires_ledger(self):
        result=self.fixture_commit()
        self.db.execute('DELETE FROM events')
        with redirect_stdout(self.output),self.assertRaises(RuntimeError):
            verify_confirmation(result,self.ledger)

if __name__=='__main__':
    unittest.main()
