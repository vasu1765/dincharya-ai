"""Focused offline continuation checks; no services, state or private inputs."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parent))
from project import SELECTORS, select_project
from recovery_checks import PHASES, next_phase, performance, evidence, observer_evidence
import observer


class NamespaceTests(unittest.TestCase):
    def test_legacy_and_new_projects(self):
        self.assertEqual(select_project({}),'dincharya-laptop-staging')
        for key,value in SELECTORS.items():
            self.assertEqual(select_project({key:'1'}),value)

    def test_every_cross_project_conflict(self):
        for a in SELECTORS:
            for b in SELECTORS:
                if a!=b:
                    with self.assertRaises(ValueError):select_project({a:'1',b:'1'})
        with self.assertRaises(ValueError):
            select_project({'DINCHARYA_STAGE2_RECOVERY_ONLY':'1','DINCHARYA_STAGE2':'unexpected'})

    def test_new_worker_uses_accepted_recorder(self):
        # Import in an isolated child so no global project state bleeds into older tests.
        import os
        env=dict(os.environ)
        for k in SELECTORS:env.pop(k,None)
        env['DINCHARYA_STAGE2_RECOVERY_ONLY']='1'
        code="import control; d=control.definition(dict(app='a',db='b',relay='r')); assert control.PROJECT=='dincharya-stage2-recovery-only'; assert d['services']['worker']['environment']=={'DINCHARYA_STAGE1_COMPLETE':'1'}; assert d['networks']['default']['internal']; assert all(not s.get('ports') for s in d['services'].values())"
        subprocess.run([sys.executable,'-B','-c',code],cwd=Path(__file__).parent,env=env,check=True,capture_output=True)


class PhaseTests(unittest.TestCase):
    def test_resume_only_completed_prefix(self):
        for n in range(len(PHASES)+1):
            prefix=set(PHASES[:n])
            self.assertEqual(next_phase(prefix,prefix),PHASES[n] if n<len(PHASES) else None)

    def test_uncertain_or_skipped_phase_never_replayed(self):
        for started,done in [({'prepare'},set()),({'arm'},{'arm'}),({'bogus'},set()),(set(),{'prepare'}),({'prepare','arm'},{'prepare'})]:
            with self.assertRaises(ValueError):next_phase(started,done)

    def test_performance_inclusive_separate(self):
        self.assertTrue(performance(10,610)['within_600_seconds'])
        self.assertFalse(performance(10,610.01)['within_600_seconds'])
        for ready in (9,float('nan'),float('inf')):
            with self.assertRaises(ValueError):performance(10,ready)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.due={'Recovery First':100,'Recovery Outage A':200,'Recovery Outage B':260,
                  'Recovery After':1200,'Staging uncertain':1260}
        self.rows=[];self.attempts=[]
        for i,(title,due) in enumerate(self.due.items(),1):
            uncertain=title=='Staging uncertain'
            self.rows.append([title,'uncertain' if uncertain else 'sent',1,None if uncertain else 101,None if uncertain else i,due])
            when=850 if 'Outage' in title else due+1
            self.attempts.append([i,int(uncertain),title,when])

    def check(self):
        evidence(self.rows,self.attempts,self.due,set(self.due),ready=800,stopped=150,recovery_started=790)

    def test_delayed_but_eligible_catchup_and_separate_performance(self):
        self.check()
        self.assertFalse(performance(150,800)['within_600_seconds'])
        self.check() # functional PASS remains possible with performance FAIL

    def test_inclusive_catchup_deadline(self):
        self.attempts[1][3]=920;self.check()
        self.attempts[1][3]=920.01
        with self.assertRaises(ValueError):self.check()

    def test_bad_receipt_and_retry_count_rejected(self):
        for column,value in [(1,'sending'),(2,2),(3,202),(4,999),(5,199)]:
            with self.subTest(column=column):
                before=copy.deepcopy(self.rows)
                self.rows[1][column]=value
                with self.assertRaises(ValueError):self.check()
                self.rows=before

    def test_duplicate_send_or_slot_rejected(self):
        self.attempts.append(self.attempts[1][:])
        with self.assertRaises(ValueError):self.check()
        self.attempts.pop();self.rows.append(self.rows[1][:])
        with self.assertRaises(ValueError):self.check()

    def test_uncertain_receipt_or_resend_rejected(self):
        self.rows[-1][4]=5
        with self.assertRaises(ValueError):self.check()
        self.rows[-1][4]=None;self.rows[-1][2]=2
        with self.assertRaises(ValueError):self.check()

    def test_premature_outage_and_nonfinite_time_rejected(self):
        self.attempts[1][3]=199
        with self.assertRaises(ValueError):self.check()
        self.attempts[1][3]=float('nan')
        with self.assertRaises(ValueError):self.check()
        self.attempts[1][3]=850
        with self.assertRaises(ValueError):
            evidence(self.rows,self.attempts,self.due,set(self.due),ready=800,stopped=210,recovery_started=790)

    def test_send_before_manual_recovery_rejected(self):
        self.attempts[1][3]=760
        with self.assertRaises(ValueError):self.check()

    def test_pending_work_cannot_hide_a_claim(self):
        rows=[['Recovery Outage A','pending',0,None,None,200]]
        evidence(rows,[],{'Recovery Outage A':200},set())
        rows[0][1]='sending'
        with self.assertRaises(ValueError):evidence(rows,[],{'Recovery Outage A':200},set())


class ObserverTests(unittest.TestCase):
    def rows(self):
        return [dict(utc=datetime.fromtimestamp(t,timezone.utc).isoformat(),state=s,revision='r',project='dincharya-stage2-recovery-only')
                for t,s in [(0,'ready'),(15,'ready'),(30,'ready'),(45,'ready'),(60,'outage'),(75,'outage'),(90,'ready'),(105,'ready')]]

    def test_continuation_trace(self):observer_evidence(self.rows(),'r',45,50,85)

    def test_wrong_project_gap_or_missing_outage(self):
        for mutate in (lambda rows:rows[0].update(project='dincharya-stage2-physical'),
                       lambda rows:rows.__delitem__(slice(1,4)),
                       lambda rows:[r.update(state='ready') for r in rows]):
            rows=self.rows();mutate(rows)
            with self.assertRaises(ValueError):observer_evidence(rows,'r',45,50,85)

    def test_observer_rejects_old_target_for_new_session(self):
        response=dict(relay='ready',due=0,sending=0,dead=0,uncertain=0,revision='r',project='dincharya-stage2-physical')
        result=subprocess.CompletedProcess([],0,json.dumps(response),'')
        with patch.object(observer.subprocess,'run',return_value=result), patch('builtins.print') as emit:
            observer.observe('pinned-alias',1,revision='r',project='dincharya-stage2-recovery-only')
        self.assertEqual(json.loads(emit.call_args_list[0].args[0])['state'],'miss')


class EncryptedExportTests(unittest.TestCase):
    def test_real_cms_stream_manifest_and_one_use(self):
        import os
        import tempfile
        import hashlib
        import contextlib
        import io
        from unittest.mock import patch
        # Import definitions only; mock every service-facing operation below.
        with patch.dict(os.environ,{},clear=False):
            import recovery_only as r
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);journal=root/'journal';journal.mkdir()
            parent=root/'private';parent.mkdir(mode=0o700)
            key=root/'invented.key';cert=root/'public.crt'
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-noenc',
                '-subj','/CN=InventedOfflineFixture','-days','1','-keyout',str(key),'-out',str(cert)],
                check=True,capture_output=True)
            der=subprocess.check_output(['openssl','x509','-in',str(cert),'-outform','DER'])
            pin=hashlib.sha256(der).hexdigest()
            for phase in PHASES[:5]:
                for suffix in ('started','done'):(journal/(phase+'.'+suffix)).write_text('0')
            values={'history':['invented-hash']*6,'prior':{'preserved':True},
                    'recipient':{'certificate':str(cert.resolve()),'fingerprint':pin}}
            for name,value in values.items():(journal/name).write_text(json.dumps(value))
            plain=b'Invented synthetic backup payload; no database connection.'
            def fake_dump(*args,**kw):
                self.assertEqual(args[0],'pg_dump')
                kw['stdout'].write(plain)
            def fake_compose(*args,**kw):return subprocess.CompletedProcess([],0,b'','')
            env={'CERT':str(cert),'CERT_SHA256':pin,'USB_STAGING_PARENT':str(parent),'REV':'r'}
            with patch.dict(os.environ,env), patch.object(r,'JOURNAL',journal), \
                 patch.object(r,'history',return_value=values['history']), \
                 patch.object(r,'inventory',return_value=values['prior']), \
                 patch.object(r,'compose',side_effect=fake_compose), \
                 patch.object(r,'sql',side_effect=fake_dump), patch.object(r,'stage') as stage, \
                 patch.object(r.subprocess,'check_output',return_value='ext4'), \
                 contextlib.redirect_stdout(io.StringIO()):
                r.export_usb()
                stage.assert_called_once_with('stop')
                with self.assertRaises(ValueError):r.export_usb()
            dest=parent/'recovery-only-usb-export'
            manifest=json.loads((dest/'restore-manifest').read_text())
            archive=dest/(manifest['digest']+'.dump.cms')
            self.assertEqual({p.name for p in dest.iterdir()},{archive.name,'restore-manifest'})
            self.assertNotIn(plain,archive.read_bytes())
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),manifest['digest'])
            self.assertEqual(manifest['history'],values['history'])
            result=subprocess.run(['openssl','cms','-decrypt','-binary','-inform','DER',
                '-inkey',str(key),'-in',str(archive)],check=True,capture_output=True)
            self.assertEqual(result.stdout,plain)
            self.assertTrue((journal/'export.done').is_file())


if __name__=='__main__':unittest.main()
