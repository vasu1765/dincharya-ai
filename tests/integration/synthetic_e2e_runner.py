"""One synthetic n8n -> Python lunar/worker -> PostgreSQL journey; no real sends.

Uses the unchanged standalone2C compose and project. No T00–T26 replay.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta
import json
from pathlib import Path
import secrets
import subprocess
import sys
import time
from uuid import uuid4

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import runner as base
sys.path[:0]=[str(base.ROOT),str(base.ROOT/'scripts')]
from source_sync import validate_schema
from database.migrate import render_migrations

ACTORS=('synthetic_e2e_owner','synthetic_e2e_calculator','synthetic_e2e_worker','synthetic_e2e_transport')
MIGRATIONS=('0001_gregorian_occurrences.sql','0002_occurrence_reminders.sql','0003_managed_legacy_boundary.sql',
 '0004_telegram_receipts.sql','0005_synthetic_reconciliation.sql','0006_synthetic_lunar_approval.sql',
 '0007_lunar_calculation_binding.sql','0008_lunar_projection_trigger_path.sql')


def workflow(key):
    return {'name':'Synthetic lunar journey','active':False,'settings':{'timezone':'Asia/Kolkata'},'nodes':[
      {'id':'e2e-webhook','name':'Synthetic request','type':'n8n-nodes-base.webhook','typeVersion':2,
       'position':[0,0],'webhookId':'synthetic-lunar-e2e','parameters':{'httpMethod':'POST','path':'synthetic-lunar-e2e','responseMode':'lastNode','options':{}}},
      {'id':'e2e-forward','name':'Existing component bridge','type':'n8n-nodes-base.httpRequest','typeVersion':4.2,
       'position':[200,0],'parameters':{'method':'POST','url':'http://mock-services:8081/journey',
        'sendHeaders':True,'headerParameters':{'parameters':[{'name':'x-synthetic-key','value':key}]},
        'sendBody':True,'specifyBody':'json','jsonBody':'={{ $json.body }}','options':{'timeout':40000}}}],
      'connections':{'Synthetic request':{'main':[[{'node':'Existing component bridge','type':'main','index':0}]]}}}


class E2ERunner(base.Runner):
    baseline=None
    def app_sql(self,statement):
        return self.compose('exec','-T','postgres-test','psql','-XAt','-v','ON_ERROR_STOP=1',
          '-v','VERBOSITY=sqlstate','-U','synthetic_test','-d','dincharya_app_test',data=statement,timeout=90).strip()

    def n8n(self,action,**data):
        result=self.compose('exec','-T','n8n-test','node','-e',(HERE/'e2e_n8n_client.js').read_text(),
               data=json.dumps({'action':action,**data}),timeout=55)
        return json.loads(result)

    def start_worker(self):
        self.worker=subprocess.Popen([sys.executable,'-B',str(HERE/'e2e_worker.py')],
             stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,
             env={'PATH':self.env['PATH'],'HOME':self.env['HOME'],'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'})
        self.worker.stdin.write(json.dumps(self.config)+'\n');self.worker.stdin.flush()
        # Bound readiness independently of any bridge/server failure.
        import selectors
        with selectors.DefaultSelector() as selector:
            selector.register(self.worker.stdout,selectors.EVENT_READ)
            base.require(bool(selector.select(20)),'Synthetic worker readiness timeout')
            base.require(self.worker.stdout.readline().strip()=='{"ready":true}','Synthetic worker failed to start')

    def stop_worker(self):
        if getattr(self,'worker',None) is None:return
        worker=self.worker
        try:
            worker.stdin.write('stop\n');worker.stdin.flush()
            worker.wait(timeout=20)
            base.require(worker.returncode==0,'Synthetic worker shutdown failed')
        finally:
            if worker.poll() is None:worker.kill();worker.wait(timeout=10)
            self.worker=None

    def request(self,operation,case='success',**values):
        return self.n8n('request',body={'user_id':101,'chat_id':101,'chat_type':'private','operation':operation,'case':case,**values})

    def tests(self):
        self.passwords={};self.worker=None
        try:self.journey_tests()
        finally:
            self.stop_worker();self.passwords.clear()
            if hasattr(self,'config'):self.config.clear()

    def journey_tests(self):
        # Disable all credential-bearing error/statement logging before provision.
        for key,value in {'log_statement':'none','log_min_error_statement':'panic','log_min_duration_statement':'-1',
           'log_min_duration_sample':'-1','log_duration':'off','log_transaction_sample_rate':'0',
           'log_parameter_max_length':'0','log_parameter_max_length_on_error':'0'}.items():
            self.app_sql(f"ALTER SYSTEM SET {key}='{value}'")
        self.app_sql('SELECT pg_reload_conf()')
        for key,value in {'log_statement':'none','log_min_error_statement':'panic','log_min_duration_statement':'-1',
           'log_min_duration_sample':'-1','log_duration':'off','log_transaction_sample_rate':'0',
           'log_parameter_max_length':'0','log_parameter_max_length_on_error':'0'}.items():
            base.require(self.app_sql('SHOW '+key)==value,'Unsafe synthetic database logging')
        base.require(self.app_sql("SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL OR "
           "(type LIKE 'host%' AND auth_method<>'scram-sha-256') OR (auth_method='trust' AND type<>'local')")=='0','SCRAM/local trust mismatch')
        base.require(self.app_sql("SELECT count(*) FROM pg_tables WHERE schemaname='public'")=='1','Unexpected initial application schema')
        self.app_sql('DROP TABLE public.synthetic_events')
        original=self.baseline.read_bytes();self.app_sql(validate_schema(original).decode())
        self.app_sql(render_migrations([base.ROOT/'database/migrations'/name for name in MIGRATIONS]))
        self.app_sql((HERE/'e2e_fixture.sql').read_text())
        for actor in ACTORS:
            self.passwords[actor]=secrets.token_hex(24)
            credential_literal="'"+self.passwords[actor]+"'"
            statement='CREATE ROLE %s LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %s'
            self.app_sql(statement % (actor,credential_literal))
        self.app_sql('GRANT dincharya_lunar_owner TO synthetic_e2e_owner; GRANT dincharya_lunar_calculator TO synthetic_e2e_calculator; '
            'GRANT dincharya_reminder_worker TO synthetic_e2e_worker; GRANT USAGE ON SCHEMA synthetic_e2e TO synthetic_e2e_transport; '
            'GRANT EXECUTE ON FUNCTION synthetic_e2e.record_attempt(bigint,text) TO synthetic_e2e_transport; '
            "INSERT INTO lunar_private.principals(role_oid,role_name,owner_subject,kind,enabled) SELECT oid,rolname,101,"
            "CASE WHEN rolname='synthetic_e2e_owner' THEN 'owner' ELSE 'calculator' END,true FROM pg_roles WHERE rolname IN ('synthetic_e2e_owner','synthetic_e2e_calculator')")
        profile=self.app_sql("SELECT lunar_private.hash('{\"synthetic_e2e\":1,\"astronomy_enabled\":false}')")
        self.app_sql("INSERT INTO lunar_private.profiles(digest,specification,enabled) VALUES('"+profile+"','{\"synthetic_e2e\":1,\"astronomy_enabled\":false}',true)")
        server=datetime.fromisoformat(self.app_sql("SELECT clock_timestamp() AT TIME ZONE 'Asia/Kolkata'"))
        fixtures={}
        for index,case in enumerate(('success','rejected','stale','cancelled','failure','uncertain')):
            due=server+timedelta(seconds=100,microseconds=index*1000);day=due.date().isoformat()
            fixture={name:str(uuid4()) for name in ('series','rule_action','rule_decision','calculation','proposal','decision','cancel_action','cancel_decision','second_calculation')}
            fixture.update(date=day,time=due.time().isoformat(),alternate_date=(due.date()+timedelta(days=1)).isoformat(),
              rule=dict(convention='purnimanta',month='chaitra',intercalation='ordinary',paksha='shukla',tithi=5,
                        repeated='review',birth_basis='explicit_rule',profile=profile),
              identity=dict(version=2,convention='purnimanta',month='chaitra',intercalation='ordinary',lunation_cycle=330,paksha='shukla',tithi=5))
            def evidence(d):return dict(status='selected',month_status='supported',date_gate='pass',kshaya=False,ambiguous=False,skipped=False,
                repeated=False,selection=d,birth_basis='explicit_rule',repetition_policy='review',interval_start=d+'T00:00:00+05:30',interval_end=d+'T23:59:59+05:30')
            fixture['evidence']=evidence(day);fixture['alternate_evidence']=evidence(fixture['alternate_date']);fixtures[case]=fixture
        key=secrets.token_hex(32)
        self.config={'docker':self.base,'compose':self.prefix,'environment':dict(self.env),
                      'passwords':self.passwords,'fixtures':fixtures,'key':key}
        self.start_worker()
        bootstrap={'workflow':workflow(key)};bootstrap['password']=self.password
        wid=self.n8n('bootstrap',**bootstrap)['id']
        print('PASS E01 isolated schema, SCRAM roles, real component process and native n8n webhook',flush=True)
        replies={};events={}
        for case in fixtures:
            preview=self.request('request',case,message='Synthetic lunar birthday '+case)
            base.require(preview.get('status')=='preview','Request did not produce synthetic preview')
            base.require(self.request('request',case,message='Synthetic lunar birthday '+case)['request']==preview['request'],'Request replay duplicated proposal')
            review=self.request('review',case,request=preview['request'])
            proposed=self.request('approve_rule',case,request=preview['request'],fingerprint=review['fingerprint'])
            base.require(proposed.get('status')=='occurrence_proposed','Explicit rule approval/occurrence proposal failed')
            replies[case]=proposed
            base.require(self.app_sql("SELECT event_id IS NULL FROM lunar_private.occurrences WHERE id='"+proposed['occurrence']+"'")=='t','Unapproved occurrence projected')
            if case=='stale':
                self.request('recalculate',case)
                decision=self.request('approve',case,request=proposed['request'],fingerprint=proposed['review']['fingerprint'])
                base.require(decision.get('status')=='decision_unavailable','Stale decision accepted')
            else:
                decision=self.request('reject' if case=='rejected' else 'approve',case,request=proposed['request'],fingerprint=proposed['review']['fingerprint'])
                base.require(decision.get('status')==('rejected' if case=='rejected' else 'approved'),'Explicit occurrence decision failed')
                if case!='rejected':events[case]=decision['event_id']
            if case=='cancelled':
                cancel=self.request('cancel',case,occurrence=proposed['occurrence'])
                base.require(self.request('approve_cancel',case,request=cancel['request'],fingerprint=cancel['review']['fingerprint']).get('status')=='approved','Cancellation failed')
        base.require(self.request('tick',user_id=202).get('status')=='denied','Foreign request accepted')
        print('PASS E02 preview, separate approvals, idempotency, rejection/staleness and cancellation',flush=True)
        pgid=self.compose('ps','-q','postgres-test').strip();pgstarted=self.inspect(pgid)['State']['StartedAt']
        self.stop_worker();self.compose('restart','n8n-test',timeout=60)
        def ready():
            try:return json.loads(self.compose('exec','-T','n8n-test','node','-e',
              "fetch('http://127.0.0.1:5678/healthz/readiness').then(r=>console.log(JSON.stringify(r.ok)))")) is True
            except base.Failure:return False
        base.bounded_wait(ready,'n8n recovery',timeout=60)
        self.start_worker()
        base.require(self.compose('ps','-q','postgres-test').strip()==pgid and self.inspect(pgid)['State']['StartedAt']==pgstarted,'PostgreSQL changed during worker/n8n restart')
        print('PASS E03 actual worker-process/n8n restart, PostgreSQL unchanged',flush=True)
        deadline=time.monotonic()+120
        while self.app_sql("SELECT clock_timestamp()>=('"+fixtures['uncertain']['date']+' '+fixtures['uncertain']['time']+"'::timestamp AT TIME ZONE 'Asia/Kolkata')")!='t':
            base.require(time.monotonic()<deadline,'Due-time wait exceeded bound');time.sleep(.2)
        with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda _:self.request('tick'),range(2)))
        self.request('tick')
        for case,state in [('success','sent'),('failure','failed'),('uncertain','uncertain')]:
            base.require(self.app_sql(f"SELECT status FROM public.reminder_deliveries WHERE event_id={int(events[case])}")==state,'Worker outcome mismatch')
            base.require(self.app_sql(f"SELECT count(*) FROM synthetic_e2e.attempts WHERE event_id={int(events[case])}")=='1','Duplicate or missing simulated attempt')
        base.require(self.app_sql(f"SELECT telegram_chat_id=101 AND telegram_message_id IS NOT NULL AND attempts=1 FROM public.reminder_deliveries WHERE event_id={int(events['success'])}")=='t','Receipt missing')
        fail_cancel=self.request('cancel','failure',occurrence=replies['failure']['occurrence'])
        base.require(self.request('approve_cancel','failure',request=fail_cancel['request'],fingerprint=fail_cancel['review']['fingerprint']).get('status')=='approved','Failed delivery cancellation failed')
        for case in ('rejected','stale'):
            base.require(self.app_sql("SELECT event_id IS NULL FROM lunar_private.occurrences WHERE id='"+replies[case]['occurrence']+"'")=='t','Unapproved case materialized')
        base.require(self.app_sql(f"SELECT enabled FROM public.schedule_events WHERE id={int(events['cancelled'])}")=='f','Cancelled event enabled')
        base.require(self.app_sql('SELECT count(*) FROM synthetic_e2e.attempts')=='3','Rejected/cancelled request sent')
        print('PASS E04 existing process_batch/SQL claims/simulated delivery/receipts and failure quarantine',flush=True)
        before=self.app_sql("SELECT json_agg(row_to_json(d) ORDER BY id) FROM public.reminder_deliveries d")
        self.stop_worker();self.compose('restart','n8n-test',timeout=60);base.bounded_wait(ready,'second n8n recovery',timeout=60);self.start_worker()
        self.request('tick');self.request('tick')
        base.require(self.app_sql('SELECT count(*) FROM synthetic_e2e.attempts')=='3','Restart resent delivery')
        base.require(self.app_sql("SELECT json_agg(row_to_json(d) ORDER BY id) FROM public.reminder_deliveries d")==before,'Restart changed terminal/cancelled history')
        base.require(self.app_sql(f"SELECT attempts FROM public.reminder_deliveries WHERE event_id={int(events['failure'])}")=='1','Cancellation reset attempts')
        base.require(self.baseline.read_bytes()==original,'Named schema changed')
        base.require(self.compose('ps','-q','postgres-test').strip()==pgid and self.inspect(pgid)['State']['StartedAt']==pgstarted,'PostgreSQL changed during second restart')
        print('PASS E05 durable restart recovery, duplicate suppression and exact delivery history',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--expected-daemon-id',required=True);parser.add_argument('--execute-approved',action='store_true');args=parser.parse_args()
    try:
        base.require(args.execute_approved,'Explicit isolated synthetic execution approval required')
        base.require(args.baseline.is_file() and not args.baseline.is_symlink(),'Exact regular schema file required')
        E2ERunner.baseline=args.baseline;base.Runner=E2ERunner;base.execute(args.expected_daemon_id)
    except Exception as error:
        print(str(error) if isinstance(error,base.Failure) else 'Synthetic E2E failed; details suppressed',file=sys.stderr);return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
