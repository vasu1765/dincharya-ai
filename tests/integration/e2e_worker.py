"""Synthetic process host for EXISTING lunar/worker adapters; no astronomy or polling.

Config/credentials arrive only on private stdin. SQL goes through real SCRAM psql
sessions inside the disposable stack. The bridge is test instrumentation, never
an application database driver or production gateway replacement.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
import json
import os
import re
import subprocess
import sys
from uuid import UUID

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from dincharya.reminder_adapters import PostgresReminders
from dincharya.reminders import process_batch, DeliveryReceipt, NotAccepted, DeliveryUncertain
from prototypes.panchang.postgres_contract import SyntheticLunarPostgres, LunarStorageError


def literal(value):
    if value is None:return 'NULL'
    if type(value) is bool:return 'true' if value else 'false'
    if type(value) is int:return str(value)
    if isinstance(value,(UUID,datetime,date)):value=value.isoformat() if hasattr(value,'isoformat') else str(value)
    if not isinstance(value,str):raise ValueError('Unsupported bound fixture value')
    return "'"+value.replace("'","''")+"'"


class Cursor:
    def __init__(self,rows):self.rows=[tuple(row.values()) for row in rows]
    def fetchone(self):return self.rows[0] if self.rows else None
    def fetchall(self):return self.rows


class PsqlConnection:
    """Real single-statement atomic SQL session; no mocks, network or libpq defaults.

    Supports only the one-statement SELECT contract used by the existing adapters.
    SELECT output is released only after psql successfully commits the transaction.
    """
    def __init__(self,config,actor):self.config=config;self.actor=actor
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def execute(self,statement,values=()):
        if not statement.startswith('SELECT ') or ';' in statement or statement.count('%s')!=len(values):
            raise ValueError('Single static parameterized SELECT required')
        chunks=statement.split('%s');bound=chunks[0]
        for value,tail in zip(values,chunks[1:]):bound+=literal(value)+tail
        # Explicit standard strings before binding, no user identifier interpolation.
        sql="BEGIN; SET LOCAL standard_conforming_strings=on; SELECT coalesce(json_agg(row_to_json(r)),'[]') FROM ("+bound+") r; COMMIT;"
        config=self.config;env=dict(config['environment']);env['PGPASSWORD']=config['passwords'][self.actor]
        argv=config['docker']+config['compose']+['exec','-T','-e','PGPASSWORD','postgres-test','psql','-XAt','-w',
             '-v','ON_ERROR_STOP=1','-v','VERBOSITY=sqlstate','-h','127.0.0.1','-U',self.actor,'-d','dincharya_app_test']
        try:result=subprocess.run(argv,input=sql,text=True,capture_output=True,env=env,timeout=30)
        finally:env.pop('PGPASSWORD',None)
        if result.returncode:raise RuntimeError('Synthetic database operation failed')
        lines=[line for line in result.stdout.splitlines() if line.startswith('[')]
        if len(lines)!=1:raise RuntimeError('Invalid synthetic database response')
        return Cursor(json.loads(lines[0]))


class SimulatedTelegram:
    """Append every attempt; intentionally NO dedupe masking worker defects."""
    def __init__(self,connect):self.connect=connect
    def send(self,payload):
        mode=payload['title'].rsplit(': ',1)[-1]
        if mode not in ('success','failure','uncertain','cancelled','rejected','stale'):raise ValueError('Unknown fixture')
        with self.connect() as conn:
            row=conn.execute('SELECT message_id FROM synthetic_e2e.record_attempt(%s,%s)',
                             (payload['event_id'],mode)).fetchone()
        if mode=='failure':raise NotAccepted('Synthetic definitive rejection')
        if mode=='uncertain':raise RuntimeError('Synthetic accepted response lost')
        return DeliveryReceipt(101,row[0])


class Journey:
    def __init__(self,config):
        self.config=config
        def connect(actor):return lambda:PsqlConnection(config,actor)
        self.owner=SyntheticLunarPostgres(connect('synthetic_e2e_owner'))
        self.calculator=SyntheticLunarPostgres(connect('synthetic_e2e_calculator'))
        self.repository=PostgresReminders(connect('synthetic_e2e_worker'),restricted_worker=True)
        self.transport=SimulatedTelegram(connect('synthetic_e2e_transport'))
        self.clock=lambda:datetime.now(timezone.utc)

    def handle(self,body):
        # Only invented private-owner envelopes, never exposed/registered in gateway.
        if (not isinstance(body,dict) or body.get('user_id')!=101 or body.get('chat_id')!=101
                or body.get('chat_type')!='private' or body.get('case') not in self.config['fixtures']):
            return {'status':'denied'}
        fixture=self.config['fixtures'][body['case']];operation=body.get('operation')
        series=UUID(fixture['series']);rule=fixture['rule'];uid=lambda key:UUID(fixture[key])
        if operation=='request':
            if body.get('message')!='Synthetic lunar birthday '+body['case']:return {'status':'denied'}
            request=self.owner.propose_series(uid('rule_action'),series,'birthday',0,rule)
            return {'status':'preview','request':request,'synthetic':True,'date':fixture['date'],
                    'time':fixture['time'],'rule':rule,'approval_required':True}
        if operation=='approve_rule':
            request=body['request'];review=self.owner.inspect_request(request)
            result=self.owner.decide(uid('rule_decision'),request,'approve',body['fingerprint'],reviewed=True)
            if result['status']!='approved':return result
            occurrence=self.calculator.record_calculation(uid('calculation'),series,1,fixture['identity'],
                              rule['profile'],fixture['evidence'],date.fromisoformat(fixture['date']))
            occurrence=UUID(occurrence) if isinstance(occurrence,str) else occurrence
            snapshot=self.owner.inspect_occurrence(occurrence)
            proposal=self.owner.propose_occurrence(uid('proposal'),occurrence,'select',1,
                 snapshot['occurrence']['revision'],snapshot['occurrence']['observation'],
                 {'date':fixture['date'],'title':'Synthetic lunar birthday: '+body['case'],'start_time':fixture['time']})
            return {'status':'occurrence_proposed','request':proposal,'occurrence':str(occurrence),
                    'review':self.owner.inspect_request(proposal)}
        if operation=='review':return self.owner.inspect_request(body['request'])
        if operation in ('approve','reject'):
            return self.owner.decide(uid('decision'),body['request'],operation,body['fingerprint'],reviewed=True)
        if operation=='cancel':
            occurrence=UUID(body['occurrence']);s=self.owner.inspect_occurrence(occurrence)
            proposal=self.owner.propose_occurrence(uid('cancel_action'),occurrence,'cancel',
                  s['series']['revision'],s['occurrence']['revision'],s['occurrence']['observation'],{})
            return {'status':'cancel_proposed','request':proposal,'review':self.owner.inspect_request(proposal)}
        if operation=='approve_cancel':
            return self.owner.decide(uid('cancel_decision'),body['request'],'approve',body['fingerprint'],reviewed=True)
        if operation=='recalculate':
            # A separate invented observation is the stale-decision fixture.
            return {'occurrence':str(self.calculator.record_calculation(uid('second_calculation'),series,1,
                 fixture['identity'],rule['profile'],fixture['alternate_evidence'],date.fromisoformat(fixture['alternate_date'])))}
        if operation=='tick':
            try:return {'status':'processed','completed':process_batch(self.repository,self.transport,self.clock,limit=1)}
            except DeliveryUncertain:return {'status':'uncertain'}
        return {'status':'denied'}


def main():
    config=json.loads(sys.stdin.readline());journey=Journey(config)
    bridge_source=(ROOT/'tests/integration/e2e_bridge.js').read_text()
    bridge=subprocess.Popen(config['docker']+config['compose']+['exec','-T','mock-services','node','-e',bridge_source],
           stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,env=config['environment'])
    bridge.stdin.write(json.dumps({'key':config['key']})+'\n');bridge.stdin.flush()
    if json.loads(bridge.stdout.readline())!={'ready':True}:raise RuntimeError('Bridge initialization failed')
    print('{"ready":true}',flush=True)
    import threading
    lock=threading.Lock()
    def dispatch(data):
        try:result=journey.handle(data['input'])
        except LunarStorageError:result={'status':'decision_unavailable'}
        except Exception:result={'status':'failed'}
        with lock:
            bridge.stdin.write(json.dumps({'id':data['id'],'result':result})+'\n');bridge.stdin.flush()
    pool=ThreadPoolExecutor(max_workers=4)
    def receive():
        for line in bridge.stdout:pool.submit(dispatch,json.loads(line))
    thread=threading.Thread(target=receive,daemon=True);thread.start()
    try:
        if sys.stdin.readline().strip()!='stop':raise RuntimeError('Invalid worker lifecycle request')
    finally:
        pool.shutdown(wait=True);bridge.stdin.close()
        bridge.wait(timeout=10)
        print('{"stopped":true}',flush=True)


if __name__=='__main__':
    try:main()
    except Exception:
        print('Synthetic worker failed; details suppressed',file=sys.stderr)
        raise SystemExit(1)
