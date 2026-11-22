"""Focused disposable tests of the new staging boundaries."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from control import definition,encrypt_command,validate_transfer
from observer import observe
from service import Recorder
from dincharya.reminders import DeliveryUncertain,Claim,process_batch


class StageTests(unittest.TestCase):
    def test_network_and_volumes(self):
        project=definition(dict(app='a',db='b',relay='c'))
        self.assertEqual(project['networks'],{'default':{'internal':True}})
        self.assertEqual(set(project['services']),{'gateway','app','db','worker','relay'})
        for role,service in project['services'].items():
            for field in ('ports','network_mode','privileged','extra_hosts','devices','env_file'):
                self.assertNotIn(field,service)
            self.assertNotIn('docker.sock',str(service))
        self.assertNotIn('socket:',str(project['services']['gateway']))
        self.assertNotIn('/run/pass',str(project['services']['worker']))
        self.assertNotIn('/cfg.json',str(project['services']['relay']))

    def test_recorder_reopen_and_uncertain(self):
        from datetime import datetime,timezone
        class Repository:
            pending=[Claim(1,'fixture',{'title':'Staging uncertain'})]
            def claim(self,now,limit):
                return self.pending
            def finish(self,claim,status,now):
                self.pending=[]
                return status=='uncertain'
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'test.db'
            a=Recorder(path).send({'title':'Staging first'})
            code="from service import Recorder; import sys; print(Recorder(sys.argv[1]).send({'title':'second'}).message_id)"
            b=subprocess.check_output([sys.executable,'-B','-c',code,str(path)],cwd=Path(__file__).parent,text=True)
            self.assertEqual((a.message_id,int(b)),(1,2))
            repo=Repository()
            tick=lambda:process_batch(repo,Recorder(path),lambda:datetime.now(timezone.utc))
            with self.assertRaises(DeliveryUncertain):
                tick()
            self.assertEqual(tick(),0)
            import sqlite3
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute('SELECT count(*),sum(uncertain) FROM attempts').fetchone(),(3,1))

    def test_observer_loss_recovery(self):
        from io import StringIO
        ok=json.dumps(dict(relay='ready',due=0,sending=0,uncertain=1,dead=0))
        with patch('observer.subprocess.run',side_effect=[OSError(),OSError(),subprocess.CompletedProcess([],0,ok)]),patch('sys.stdout',new_callable=StringIO) as out,patch('sys.stderr',new_callable=StringIO):
            observe('fixture',3,0)
        self.assertEqual([json.loads(s)['state'] for s in out.getvalue().splitlines()],['miss','outage','attention'])

    def test_fenced_transfer(self):
        from types import SimpleNamespace
        import time
        with tempfile.TemporaryDirectory() as tmp:
            key,pub,ticket,sig=[Path(tmp)/n for n in ('key','pub','ticket','sig')]
            # The operator signs with RSA/SHA-256, matching the controller.
            subprocess.run(['openssl','genrsa','-out',key,'2048'],check=True,capture_output=True)
            subprocess.run(['openssl','rsa','-in',key,'-pubout','-out',pub],check=True,capture_output=True)
            a=SimpleNamespace(ticket=ticket,signature=sig,authority=pub,authority_sha=hashlib.sha256(pub.read_bytes()).hexdigest(),
                              daemon='destination',revision='a'*40)
            v=dict(source='source',destination=a.daemon,revision=a.revision,project='dincharya-laptop-staging',fenced_at=int(time.time()))
            def sign():
                ticket.write_text(json.dumps(v))
                subprocess.run(['openssl','dgst','-sha256','-sign',key,'-out',sig,ticket],check=True)
            sign()
            validate_transfer(a)
            v['destination']='elsewhere'
            sign()
            with self.assertRaises(ValueError):
                validate_transfer(a)
            v.update(destination=a.daemon,fenced_at=int(time.time())-3700)
            sign()
            with self.assertRaises(ValueError):
                validate_transfer(a)
            ticket.write_text('{}')
            with self.assertRaises(subprocess.CalledProcessError):
                validate_transfer(a)

    def test_encrypted_stream(self):
        with tempfile.TemporaryDirectory() as tmp:
            key,cert,path=[Path(tmp)/n for n in ('key','cert','backup')]
            def run(*args,**kw):
                return subprocess.run(args,check=True,capture_output=True,**kw)
            run('openssl','req','-x509','-newkey','rsa:2048','-noenc','-subj','/CN=Synthetic',
                '-days','1','-keyout',key,'-out',cert)
            fingerprint=hashlib.sha256(run('openssl','x509','-in',cert,'-outform','DER').stdout).hexdigest()
            data=b'Invented restore fixture'*30
            run(*encrypt_command(fingerprint,cert,path),input=data)
            decrypt=['openssl','cms','-decrypt','-binary','-inform','DER','-inkey',key,'-in',path]
            blob=path.read_bytes()
            self.assertNotIn(data,blob)
            self.assertEqual(run(*decrypt).stdout,data)
            with self.assertRaises(ValueError):
                encrypt_command('0'*64,cert,path)
            path.write_bytes(blob[:-32])
            with self.assertRaises(subprocess.CalledProcessError):
                run(*decrypt)

if __name__=='__main__':
    unittest.main()
