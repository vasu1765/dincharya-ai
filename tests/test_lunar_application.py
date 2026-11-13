"""Focused application security/SDK checks. No PostgreSQL or external API calls."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch

from dincharya.lunar_service import LunarService,ReviewTokens,envelope,connection_factory,live_transport
from dincharya.lunar_runtime import read_private,build_service,validate_test_bot

ROOT=Path(__file__).resolve().parents[1]
AVAILABLE=all(importlib.util.find_spec(n) is not None for n in ('telegram','httpx','psycopg'))

class ApplicationSecurityTests(unittest.TestCase):
 def service(self):
  connect=Mock(side_effect=AssertionError('Must not connect'))
  return LunarService(connect,connect,connect,{'synthetic':True,'astronomy_enabled':False,'fixtures':{}},'a'*64,'b'*64,'c'*64)
 def test_signature_precedes_database_work(self):
  s=self.service();v,_=envelope('a'*64,{'operation':'request','kind':'birthday','fixture':'anything'},'10')
  self.assertEqual(s.handle(v,'0'*64),{'status':'denied'})
 def test_worker_signature_cannot_authorize_owner_command(self):
  s=self.service();v,signature=envelope('b'*64,{'operation':'request','kind':'birthday','fixture':'anything'},'10')
  self.assertEqual(s.handle(v,signature),{'status':'denied'})
 def test_expired_envelope_rejects(self):
  s=self.service();v,signature=envelope('a'*64,{'operation':'request'},'10',clock=lambda:1)
  self.assertEqual(s.handle(v,signature),{'status':'denied'})
 def test_body_actor_fields_never_become_authority(self):
  s=self.service();v,signature=envelope('a'*64,{'operation':'request','kind':'birthday','fixture':'x','user_id':101},'10')
  self.assertEqual(s.handle(v,signature)['status'],'unavailable')
 def test_disabled_delivery_never_claims(self):
  s=self.service();v,signature=envelope('b'*64,{'operation':'tick'},'10')
  self.assertEqual(s.handle(v,signature),{'status':'delivery_disabled'})
 def test_keys_must_be_strong_and_separate(self):
  with self.assertRaises(ValueError):LunarService(None,None,None,{},'a'*64,'a'*64,'a'*64)
 def test_review_token_detects_tamper_and_expiry(self):
  now=[100];tokens=ReviewTokens('a'*64,clock=lambda:now[0]);token=tokens.issue({'request':1,'fingerprint':'x','stage':'rule'})
  self.assertEqual(tokens.read(token)['request'],1)
  with self.assertRaises(Exception):tokens.read(token+'changed')
  now[0]=2000
  with self.assertRaises(ValueError):tokens.read(token)
 def test_real_transport_requires_explicit_authorization(self):
  post=Mock()
  with self.assertRaises(ValueError):live_transport(post,'unused',101)
  post.assert_not_called()
 def test_live_runtime_flag_stops_before_database_or_api(self):
  with patch('dincharya.lunar_runtime.connection_factory') as factory:
   with self.assertRaises(ValueError):build_service({'delivery_enabled':True})
  factory.assert_not_called()
 def test_textual_false_cannot_enable_live_transport(self):
  with patch('dincharya.lunar_runtime.connection_factory') as factory:
   with self.assertRaises(ValueError):build_service({'delivery_enabled':'false'},live_approved=True)
  factory.assert_not_called()
 def test_connections_reject_production_and_ambient_pg_settings(self):
  for value in [dict(host='production',dbname='main',user='x'),dict(host='127.0.0.1',port=5432,dbname='dincharya_app_test',user='x')]:
   value['password']='invented'
   with self.assertRaises(ValueError):connection_factory(value)
  value=dict(host='/tmp/unused',dbname='dincharya_app_test',user='synthetic');value['password']='invented'
  with patch.dict(os.environ,{'PGHOST':'not-used'}):
   with self.assertRaises(ValueError):connection_factory(value)()
 def test_test_bot_pin_rejects_wrong_owner_token_and_types(self):
  info={'token':str(123456)+':'+'x'*24,'owner_id':101,'bot_id':123456}
  validate_test_bot(info,101)
  for changed in [dict(info,owner_id=202),dict(info,token='different'),dict(info,owner_id=True)]:
   with self.assertRaises(ValueError):validate_test_bot(changed,101)
 def test_ambiguous_storage_failure_does_not_recommend_duplicate_reminder(self):
  from prototypes.panchang.postgres_contract import LunarStorageError
  s=self.service();s.catalog.fixtures={'x':{'purpose':'birthday','rule':{}}}
  s.owner.propose_series=Mock(side_effect=LunarStorageError('private detail'))
  value,signature=envelope('a'*64,{'operation':'request','kind':'birthday','fixture':'x'},'10')
  reply=s.handle(value,signature)['reply']
  self.assertIn('inspect',reply);self.assertNotIn('fresh preview',reply);self.assertNotIn('private detail',reply)
 def test_new_status_migration_is_in_the_transactional_renderer(self):
  import hashlib
  from database.migrate import render_migrations
  path=ROOT/'database/migrations/0009_lunar_delivery_status.sql'
  text=render_migrations([path])
  self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(),text)
  self.assertIn('lunar_api.owner_identity',text);self.assertTrue(text.endswith('COMMIT;\n'))
 def test_private_config_mode_symlink_and_repository_boundaries(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'config.json';path.write_text('{}');path.chmod(0o600)
   self.assertEqual(read_private(path),{})
   path.chmod(0o644)
   with self.assertRaises(ValueError):read_private(path)
   link=Path(directory)/'link';link.symlink_to(path)
   with self.assertRaises(OSError):read_private(link)
  with tempfile.TemporaryDirectory(dir=ROOT) as directory:
   path=Path(directory)/'config.json';path.write_text('{}');path.chmod(0o600)
   with self.assertRaises(ValueError):read_private(path)


@unittest.skipUnless(AVAILABLE,'Optional acceptance SDK/driver unavailable')
class GatewaySDKTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  sys.path.insert(0,str(ROOT/'tests/integration'))
  from m2g_bot import build
  self.commands=Mock();self.ticks=Mock();self.commands.call.return_value={'reply':'synthetic preview'}
  self.app,self.wire=build(self.commands,self.ticks,interval=60);await self.app.initialize()
 async def asyncTearDown(self):
  await self.app.shutdown();sys.path.remove(str(ROOT/'tests/integration'))
 async def send(self,text,**who):
  from m2g_bot import update
  await self.app.process_update(update(self.app,text,10,**who))
 async def test_actual_sdk_refuses_foreign_group_edited_and_bot_updates(self):
  for who in [dict(user=202),dict(chat=202),dict(chat_type='group'),dict(edited=True),dict(is_bot=True)]:await self.send('/lunar_birthday x',**who)
  self.commands.call.assert_not_called();self.assertEqual(self.wire.messages,[])
 async def test_actual_sdk_passes_no_body_identity_and_uses_update_nonce(self):
  await self.send('/lunar_birthday approved-fixture')
  self.commands.call.assert_called_once_with({'operation':'request','kind':'birthday','fixture':'approved-fixture'},'10')
  self.assertEqual(self.wire.messages,['synthetic preview'])
 async def test_missing_argument_never_reaches_database(self):
  await self.send('/approve_lunar')
  self.commands.call.assert_not_called()
 async def test_single_polling_owner_and_live_disabled_default(self):
  from lunar_handlers import register_lunar
  self.assertEqual(len(self.app.job_queue.jobs()),1)
  with self.assertRaises(ValueError):register_lunar(self.app,101,self.commands,self.ticks)
 async def test_live_prepare_gate_precedes_secret_file_or_docker(self):
  import m2g_live_prepare
  args=['test','--credentials','/tmp/not-opened.json','--baseline','/tmp/not-opened.sql','--expected-daemon-id','not-used']
  with patch.object(sys,'argv',args),patch.object(m2g_live_prepare,'read_private') as read,patch('builtins.print'):
   self.assertEqual(m2g_live_prepare.main(),1)
  read.assert_not_called()
 async def test_separate_commands_not_freeform_identity_text(self):
  await self.send('/lunar_anniversary anniversary')
  self.assertEqual(self.commands.call.call_args.args[0]['kind'],'wedding_anniversary')
  self.assertNotIn('user_id',self.commands.call.call_args.args[0])

if __name__=='__main__':unittest.main()
