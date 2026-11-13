"""Offline adapter/transaction and migration packaging checks; no DB execution."""
from contextlib import redirect_stderr
from io import StringIO
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from database.migrate import render_migrations
from prototypes.panchang.postgres_contract import SyntheticLunarPostgres, LunarStorageError

ROOT=Path(__file__).resolve().parents[1]
MIGRATION=ROOT/'database/migrations/0006_synthetic_lunar_approval.sql'


class Transaction:
    def __init__(self, *, result=None, execute_error=None, commit_error=None):
        self.result=result; self.execute_error=execute_error; self.commit_error=commit_error
        self.calls=[];self.committed=False;self.rolled_back=False

    def __enter__(self):
        return self

    def execute(self, statement, values):
        self.calls.append((statement,values))
        if self.execute_error:
            raise self.execute_error
        return Mock(fetchone=lambda:(self.result,))

    def __exit__(self, kind, value, trace):
        if kind:
            self.rolled_back=True
        elif self.commit_error:
            raise self.commit_error
        else:
            self.committed=True


class LunarAdapterTests(unittest.TestCase):
    def test_init_and_import_have_no_connection_side_effect(self):
        factory=Mock(side_effect=AssertionError('must not connect'))
        SyntheticLunarPostgres(factory)
        factory.assert_not_called()

    def test_parameterized_payload_and_commit_before_return(self):
        tx=Transaction(result=123);factory=Mock(return_value=tx);adapter=SyntheticLunarPostgres(factory)
        payload={'title':"'); DROP TABLE public.schedule_events; --"}
        result=adapter.propose_occurrence(uuid4(),uuid4(),'select',1,0,1,payload)
        self.assertEqual(result,123);self.assertTrue(tx.committed)
        sql,values=tx.calls[0];self.assertNotIn('DROP',sql)
        self.assertEqual(json.loads(values[-1]),payload);factory.assert_called_once()

    def test_statement_failure_rolls_back_sanitizes_and_does_not_retry(self):
        tx=Transaction(execute_error=RuntimeError('private connection payload'))
        factory=Mock(return_value=tx);adapter=SyntheticLunarPostgres(factory)
        with self.assertRaises(LunarStorageError) as error:
            adapter.decide(uuid4(),12,'approve','a'*64,reviewed=True)
        self.assertNotIn('private',str(error.exception));self.assertTrue(tx.rolled_back)
        factory.assert_called_once();self.assertEqual(len(tx.calls),1)

    def test_commit_failure_does_not_return_success_or_retry(self):
        tx=Transaction(result={'status':'approved'},commit_error=RuntimeError('sensitive detail'))
        factory=Mock(return_value=tx);adapter=SyntheticLunarPostgres(factory)
        with self.assertRaises(LunarStorageError):adapter.decide(uuid4(),12,'approve','b'*64,reviewed=True)
        factory.assert_called_once();self.assertFalse(tx.committed)

    def test_same_action_replay_preserves_exact_parameters(self):
        tx=Transaction(result={'status':'approved'});adapter=SyntheticLunarPostgres(lambda:tx)
        action=uuid4()
        first=adapter.decide(action,12,'approve','c'*64,reviewed=True,force=True)
        second=adapter.decide(action,12,'approve','c'*64,reviewed=True,force=True)
        self.assertEqual(first,second);self.assertEqual(tx.calls[0],tx.calls[1])
        self.assertEqual(tx.calls[0][1][0],action)

    def test_explicit_review_defaults_false_and_no_actor_parameter(self):
        tx=Transaction(result={});adapter=SyntheticLunarPostgres(lambda:tx)
        adapter.decide(uuid4(),1,'approve','d'*64)
        self.assertEqual(tx.calls[0][1][-2:],(False,False))
        with self.assertRaises(TypeError):adapter.decide(uuid4(),1,'approve','d'*64,user_id=101)
        self.assertFalse(hasattr(adapter,'send'));self.assertFalse(hasattr(adapter,'claim'))

    def test_local_validation_before_connect(self):
        factory=Mock();adapter=SyntheticLunarPostgres(factory)
        with self.assertRaises(ValueError):adapter.propose_series('not-uuid',uuid4(),'birthday',0,{})
        with self.assertRaises(ValueError):adapter.propose_series(uuid4(),uuid4(),'birthday',0,{'x':float('nan')})
        factory.assert_not_called()

    def test_all_api_signatures_bind_values_and_return_detached_snapshots(self):
        tx=Transaction(result={'immutable':{'value':1}});adapter=SyntheticLunarPostgres(lambda:tx)
        a,s,o=uuid4(),uuid4(),uuid4()
        calls=[lambda:adapter.propose_series(a,s,'birthday',0,{}),
               lambda:adapter.record_calculation(a,s,1,{},'b'*64,{},None),
               lambda:adapter.inspect_occurrence(o),lambda:adapter.inspect_series(s),lambda:adapter.inspect_request(1),
               lambda:adapter.propose_occurrence(a,o,'cancel',1,1,1,{}),
               lambda:adapter.propose_series_cancel(a,s,1,[])]
        for invoke in calls:
            result=invoke();result['immutable']['value']=2
            self.assertEqual(tx.result['immutable']['value'],1)
            sql,params=tx.calls[-1];self.assertEqual(sql.count('%s'),len(params))


class LunarPackagingTests(unittest.TestCase):
    def test_numbered_migration_renders_offline_with_checksum_and_transaction(self):
        paths=sorted((ROOT/'database/migrations').glob('000[1-6]_*.sql'))
        self.assertEqual(len(paths),6)
        text=render_migrations(paths)
        self.assertIn(hashlib.sha256(MIGRATION.read_bytes()).hexdigest(),text)
        self.assertTrue(text.endswith('COMMIT;\n'))
        self.assertLess(text.index('pg_advisory_xact_lock(20261112,2)'),text.index('CREATE SCHEMA lunar_private'))

    def test_synthetic_environment_and_nonlogin_security_definers(self):
        # Structural regression, NOT proof of SQL runtime/authorization semantics.
        text=MIGRATION.read_text()
        self.assertIn("current_database()<>'dincharya_app_test'",text)
        self.assertIn("session_user<>'synthetic_test'",text)
        signatures=re.findall(r'CREATE FUNCTION (lunar_api\.\w+)\(',text)
        self.assertEqual(set(signatures),{'lunar_api.'+name for name in ('propose_series','record_calculation',
            'propose_occurrence','inspect_occurrence','inspect_series','inspect_request','propose_series_cancel','decide')})
        for function in signatures:
            header=text.split('CREATE FUNCTION '+function+'(',1)[1].split('AS $$',1)[0]
            self.assertIn('SECURITY DEFINER',header)
            self.assertIn('SET search_path=pg_catalog,pg_temp',header)
        self.assertEqual(text.count('CREATE TABLE lunar_private.'),6)
        self.assertNotIn('CREATE TABLE public.reminder',text)

    def test_runtime_case_registry_is_finite_and_not_a_pass_claim(self):
        path=ROOT/'tests/integration/lunar_checks.py'
        spec=importlib.util.spec_from_file_location('lunar_test_checks',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(module.CASES,tuple('T%02d'%n for n in range(27)))
        tree=ast.parse(path.read_text())
        labels=[node.args[0].value for node in ast.walk(tree) if isinstance(node,ast.Call)
                and isinstance(node.func,ast.Name) and node.func.id=='done']
        self.assertEqual(labels,list(module.CASES))
        with self.assertRaises(ValueError):module.call_sql('decide; DROP SCHEMA public')
        self.assertEqual(module.literal("a'b"),"'a''b'")

    def test_runner_without_approval_exits_before_docker_or_schema_access(self):
        directory=str(ROOT/'tests/integration');sys.path.insert(0,directory)
        try:
            spec=importlib.util.spec_from_file_location('lunar_focused_runner',Path(directory)/'focused_application_runner.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            args=['runner','--baseline','/tmp/not-opened-lunar-schema.sql','--expected-daemon-id','not-queried','--case','lunar']
            with patch.object(sys,'argv',args),patch.object(module,'execute') as execute,redirect_stderr(StringIO()):
                self.assertEqual(module.main(),1)
                execute.assert_not_called()
        finally:
            sys.path.remove(directory)


if __name__=='__main__':unittest.main()
