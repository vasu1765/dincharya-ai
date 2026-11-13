"""Offline scaffolding guards. Actual evidence comes from isolated runtime runner."""
from contextlib import redirect_stderr
from datetime import datetime,timezone
import importlib.util
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
worker=load('synthetic_e2e_worker','tests/integration/e2e_worker.py')
runner=load('synthetic_e2e_runner','tests/integration/synthetic_e2e_runner.py')

class SyntheticE2ETests(unittest.TestCase):
 def test_literal_binding_keeps_injection_inside_constant(self):
  self.assertEqual(worker.literal("a'); SELECT 1; --"),"'a''); SELECT 1; --'")
  self.assertEqual(worker.literal(None),'NULL');self.assertEqual(worker.literal(True),'true')
  self.assertEqual(worker.literal(101),'101')
  for value in [uuid4(),datetime.now(timezone.utc)]:self.assertTrue(worker.literal(value).startswith("'"))
  with self.assertRaises(ValueError):worker.literal({})

 def test_real_connection_bridge_uses_scram_stdin_not_secret_argv(self):
  config={'environment':{'PATH':'/usr/bin'},'passwords':{'actor':'synthetic-only-marker'},
          'docker':['docker'],'compose':['compose']}
  output='BEGIN\nSET\n[{"result":{"status":"approved"}}]\nCOMMIT\n'
  with patch.object(worker.subprocess,'run',return_value=subprocess.CompletedProcess([],0,output,'')) as command:
   result=worker.PsqlConnection(config,'actor').execute('SELECT example(%s)',('value',)).fetchone()
  self.assertEqual(result,({'status':'approved'},))
  args=command.call_args
  self.assertNotIn('synthetic-only-marker',str(args.args[0]))
  self.assertIn("SELECT example('value')",args.kwargs['input']);self.assertTrue(args.kwargs['input'].endswith('COMMIT;'))
  self.assertNotIn('PGPASSWORD',config['environment'])

 def test_failed_commit_output_cannot_be_returned_as_success(self):
  config={'environment':{},'passwords':{'actor':'synthetic-only-marker'},'docker':[],'compose':[]}
  with patch.object(worker.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'[{"result":true}]','private error')):
   with self.assertRaisesRegex(RuntimeError,'Synthetic database operation failed'):
    worker.PsqlConnection(config,'actor').execute('SELECT 1')

 def test_bridge_rejects_unbounded_sql_before_runtime(self):
  for sql in ['DELETE FROM example','SELECT 1; SELECT 2','SELECT %s']:
   with self.assertRaises(ValueError):worker.PsqlConnection({},'actor').execute(sql)

 def test_native_n8n_workflow_has_no_code_or_second_schedule(self):
  flow=runner.workflow('a'*64)
  self.assertEqual({n['type'] for n in flow['nodes']},{'n8n-nodes-base.webhook','n8n-nodes-base.httpRequest'})
  self.assertIn('http://mock-services:8081/journey',json.dumps(flow))
  self.assertFalse(flow['active'])

 def test_gate_stops_before_docker_and_schema_access(self):
  args=['test','--baseline','/tmp/not-opened.sql','--expected-daemon-id','not-used']
  with patch.object(sys,'argv',args),patch.object(runner.base,'execute') as execute,redirect_stderr(StringIO()):
   self.assertEqual(runner.main(),1)
  execute.assert_not_called()

 def test_foreign_envelope_never_calls_database(self):
  service=worker.Journey.__new__(worker.Journey);service.config={'fixtures':{'success':{}}}
  for body in [None,{},dict(user_id=202,chat_id=101,chat_type='private',case='success'),
               dict(user_id=101,chat_id=101,chat_type='group',case='success')]:
   self.assertEqual(service.handle(body),{'status':'denied'})

if __name__=='__main__':unittest.main()
