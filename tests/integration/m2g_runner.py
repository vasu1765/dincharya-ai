"""Actual SDK gateway + n8n + psycopg + existing worker; Telegram wire simulated."""
import argparse
import asyncio
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import secrets
import selectors
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from synthetic_e2e_runner import E2ERunner,MIGRATIONS,ACTORS
from m2g_relay import UnixTCPRelay
import runner as base
sys.path[:0]=[str(base.ROOT),str(base.ROOT/'scripts'),str(base.ROOT/'telegram-gateway')]
from database.migrate import render_migrations
from source_sync import validate_schema
from dincharya.lunar_service import connection_factory,envelope
from lunar_handlers import OrchestrationClient


class M2GRunner(E2ERunner):
    owner_id=101
    due_seconds=120
    server_script='m2g_server.py'
    migrations=(*MIGRATIONS,'0009_lunar_delivery_status.sql')
    relay_json_denials=False
    relay_timeout_ms=None
    def checkpoint(self, stage):pass
    def configure_service(self):pass
    def tests(self):
        with tempfile.TemporaryDirectory(prefix='m2g-') as directory:
            self.directory=Path(directory);self.service=None;self.bridge=None;self.relays=[]
            try:self.setup();asyncio.run(self.journey())
            finally:
                self.stop_service()
                if self.bridge:
                    self.bridge.stdin.close()
                    try:self.bridge.wait(timeout=10)
                    except subprocess.TimeoutExpired:self.bridge.kill();self.bridge.wait(timeout=5)
                for relay in self.relays:relay.close()

    def setup(self):
        import httpx
        self.checkpoint('database logging and authentication')
        settings={'log_statement':'none','log_min_error_statement':'panic','log_min_duration_statement':'-1',
          'log_min_duration_sample':'-1','log_duration':'off','log_transaction_sample_rate':'0',
          'log_parameter_max_length':'0','log_parameter_max_length_on_error':'0'}
        for key,value in settings.items():self.app_sql(f"ALTER SYSTEM SET {key}='{value}'")
        self.app_sql('SELECT pg_reload_conf()')
        for key,value in settings.items():base.require(self.app_sql('SHOW '+key)==value,'Logging boundary mismatch')
        base.require(self.app_sql("SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL OR "
          "(type LIKE 'host%' AND auth_method<>'scram-sha-256') OR (auth_method='trust' AND type<>'local')")=='0','SCRAM boundary mismatch')
        self.checkpoint('fresh database')
        base.require(self.app_sql("SELECT count(*) FROM pg_tables WHERE schemaname='public'")=='1','Fresh application DB required')
        self.app_sql('DROP TABLE public.synthetic_events')
        self.checkpoint('schema initialization')
        self.original=self.baseline.read_bytes();self.app_sql(validate_schema(self.original).decode())
        self.checkpoint('migration application')
        self.app_sql(render_migrations([base.ROOT/'database/migrations'/n for n in self.migrations]))
        self.checkpoint('synthetic transport fixture')
        self.app_sql((HERE/'e2e_fixture.sql').read_text())
        self.checkpoint('database identities and permissions')
        passwords={}
        for actor in ACTORS:
            passwords[actor]=secrets.token_hex(24);credential_literal="'"+passwords[actor]+"'"
            self.app_sql(('CREATE ROLE %s LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %s')%(actor,credential_literal))
        self.app_sql('GRANT dincharya_lunar_owner TO synthetic_e2e_owner; GRANT dincharya_lunar_calculator TO synthetic_e2e_calculator; '
           'GRANT dincharya_reminder_worker TO synthetic_e2e_worker; GRANT USAGE ON SCHEMA synthetic_e2e TO synthetic_e2e_transport; '
           'GRANT EXECUTE ON FUNCTION synthetic_e2e.record_attempt(bigint,text) TO synthetic_e2e_transport; '
           f"INSERT INTO lunar_private.principals(role_oid,role_name,owner_subject,kind,enabled) SELECT oid,rolname,{self.owner_id},"
           "CASE WHEN rolname='synthetic_e2e_owner' THEN 'owner' ELSE 'calculator' END,true FROM pg_roles WHERE rolname IN ('synthetic_e2e_owner','synthetic_e2e_calculator')")
        self.profile=self.app_sql("SELECT lunar_private.hash('{\"m2g_synthetic\":1,\"astronomy_enabled\":false}')")
        self.app_sql("INSERT INTO lunar_private.profiles(digest,specification,enabled) VALUES('"+self.profile+"','{\"m2g_synthetic\":1,\"astronomy_enabled\":false}',true)")
        self.checkpoint('local socket relays')
        pg=self.directory/'pg';pg.mkdir(mode=0o700)
        self.relays.append(UnixTCPRelay(pg/'.s.PGSQL.5432',self.base,self.prefix,self.env,'postgres-test',5432))
        self.n8n_socket=str(self.directory/'n8n.sock')
        self.relays.append(UnixTCPRelay(self.n8n_socket,self.base,self.prefix,self.env,'n8n-test',5678))
        self.config={'owner_id':self.owner_id,'service_socket':str(self.directory/'service.sock'),'connections':{},
            'command_key':secrets.token_hex(32),'tick_key':secrets.token_hex(32),'review_key':secrets.token_hex(32),
            'catalog':{'synthetic':True,'astronomy_enabled':False,'fixtures':{}},'delivery_enabled':False}
        for key,actor in [('owner',ACTORS[0]),('calculator',ACTORS[1]),('worker',ACTORS[2])]:
            self.config['connections'][key]={'host':str(pg),'dbname':'dincharya_app_test','user':actor}
            self.config['connections'][key]['password']=passwords[actor]
        self.config['transport_connection']={'host':str(pg),'dbname':'dincharya_app_test','user':ACTORS[3]}
        self.config['transport_connection']['password']=passwords[ACTORS[3]]
        server_time=datetime.fromisoformat(self.app_sql("SELECT clock_timestamp() AT TIME ZONE 'Asia/Kolkata'"))
        for idx,name in enumerate(('success','anniversary','rejected','stale','cancelled','failure','uncertain')):
            due=server_time+timedelta(seconds=self.due_seconds,microseconds=idx*1000);day=due.date().isoformat()
            rule=dict(convention='purnimanta',month='chaitra',intercalation='ordinary',paksha='shukla',tithi=5,
                repeated='review',birth_basis='explicit_rule',profile=self.profile)
            self.config['catalog']['fixtures'][name]={'purpose':'wedding_anniversary' if name=='anniversary' else 'birthday',
              'rule':rule,'date':day,'time':due.time().isoformat(),'title':'Synthetic lunar fixture: '+name,
              'identity':dict(version=2,convention='purnimanta',month='chaitra',intercalation='ordinary',lunation_cycle=330,paksha='shukla',tithi=5),
              'evidence':dict(status='selected',month_status='supported',date_gate='pass',kshaya=False,ambiguous=False,skipped=False,
                repeated=False,selection=day,birth_basis='explicit_rule',repetition_policy='review',
                interval_start=day+'T00:00:00+05:30',interval_end=day+'T23:59:59+05:30')}
        self.checkpoint('calculation profile and migration checksums')
        self.configure_service()
        self.checkpoint('application service startup')
        self.start_service()
        self.checkpoint('native n8n relay bootstrap')
        key=secrets.token_hex(32)
        self.bridge=subprocess.Popen(self.base+self.prefix+['exec','-T','mock-services','node','-e',(HERE/'e2e_bridge.js').read_text()],
           stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,env=self.env)
        self.bridge.stdin.write(json.dumps({'key':key})+'\n');self.bridge.stdin.flush()
        base.require(json.loads(self.bridge.stdout.readline())=={'ready':True},'HTTP relay not ready')
        self.bridge_pool=ThreadPoolExecutor(max_workers=8)
        def forward(data):
            try:
                with httpx.Client(transport=httpx.HTTPTransport(uds=self.config['service_socket']),
                                  timeout=42 if self.relay_timeout_ms else 30,trust_env=False) as client:
                    r=client.post('http://local/lunar',json=data['input'],headers={'x-dincharya-signature':data['signature']})
                    result=r.json()
            except Exception:result={'status':'unavailable'}
            with self.bridge_lock:
                self.bridge.stdin.write(json.dumps({'id':data['id'],'result':result})+'\n');self.bridge.stdin.flush()
        self.bridge_lock=threading.Lock()
        def receive():
            for line in self.bridge.stdout:self.bridge_pool.submit(forward,json.loads(line))
        threading.Thread(target=receive,daemon=True).start()
        flow=json.loads((base.ROOT/'workflows/m2g-lunar-acceptance.json').read_text())
        target=flow['nodes'][1]['parameters'];target['url']='http://mock-services:8081/journey'
        if self.relay_timeout_ms:
            target['options']['timeout']=self.relay_timeout_ms
        target['headerParameters']['parameters'].append({'name':'x-synthetic-key','value':key})
        if self.relay_json_denials:
            target['options']['response']={'response':{'neverError':True,'responseFormat':'json'}}
        bootstrap={'workflow':flow};bootstrap['password']=self.password
        self.n8n('bootstrap',**bootstrap)
        self.http=httpx.Client(transport=httpx.HTTPTransport(uds=self.n8n_socket),timeout=30,trust_env=False)
        self.commands=OrchestrationClient(self.http,'http://n8n/webhook/m2g-lunar',self.config['command_key'])
        self.ticks=OrchestrationClient(self.http,'http://n8n/webhook/m2g-lunar',self.config['tick_key'])
        print('PASS G01 real psycopg/scoped roles, signed n8n orchestration and application HTTP service',flush=True)

    def start_service(self):
        self.service=subprocess.Popen([sys.executable,'-B',str(HERE/self.server_script)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
          stderr=subprocess.DEVNULL,text=True,env={'PATH':self.env['PATH'],'HOME':str(self.directory),'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'})
        self.service.stdin.write(json.dumps(self.config)+'\n');self.service.stdin.flush()
        with selectors.DefaultSelector() as poll:
            poll.register(self.service.stdout,selectors.EVENT_READ)
            base.require(bool(poll.select(20)) and self.service.stdout.readline().strip()=='{"ready":true}','Real application service failed to start')
    def stop_service(self):
        if not self.service:return
        process=self.service
        try:
            if process.poll() is None:process.stdin.write('stop\n');process.stdin.flush();process.wait(timeout=20)
            base.require(process.returncode==0,'Application service shutdown failed')
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=5)
            self.service=None

    async def journey(self):
        import httpx
        from m2g_bot import build,update
        app,wire=build(self.commands,self.ticks,interval=1);await app.initialize();await app.start()
        uid=100
        async def command(text,**who):
            nonlocal uid
            uid+=1;before=len(wire.messages)
            await app.process_update(update(app,text,uid,**who))
            return wire.messages[-1] if len(wire.messages)>before else None
        def token(reply,command_name):return reply.split('/'+command_name+' ',1)[1].splitlines()[0]
        occurrences={};requests={}
        try:
            for who in [dict(user=202),dict(chat=202),dict(chat_type='group'),dict(is_bot=True),dict(edited=True)]:
                base.require(await command('/lunar_birthday success',**who) is None,'SDK authentication failure')
            base.require(self.app_sql('SELECT count(*) FROM lunar_private.series')=='0','Unauthorized update created series')
            for name in self.config['catalog']['fixtures']:
                reply=await command(('/lunar_anniversary ' if name=='anniversary' else '/lunar_birthday ')+name)
                base.require(reply and 'SYNTHETIC' in reply,'SDK preview missing')
                first_token=token(reply,'approve_lunar_rule')
                # Same SDK Update identity/text replay cannot duplicate a series.
                count=self.app_sql('SELECT count(*) FROM lunar_private.series')
                await app.process_update(update(app,('/lunar_anniversary ' if name=='anniversary' else '/lunar_birthday ')+name,uid))
                base.require(self.app_sql('SELECT count(*) FROM lunar_private.series')==count,'Telegram replay duplicated series')
                reply=await command('/approve_lunar_rule '+first_token)
                base.require(reply and 'Approve separately' in reply,'Rule approval did not produce occurrence preview')
                occurrence=reply.split('Occurrence ',1)[1].splitlines()[0];occurrences[name]=occurrence
                decision_token=token(reply,'approve_lunar');requests[name]=decision_token
                if name=='stale':
                    # Approved rule revision change invalidates the old observation snapshot.
                    self.app_sql("BEGIN; SELECT pg_advisory_xact_lock(20261112,1); UPDATE lunar_private.occurrences SET observation=observation+1 WHERE id='"+occurrence+"'; COMMIT;")
                    reply=await command('/approve_lunar '+decision_token)
                    base.require('unavailable or changed' in reply,'Stale approval accepted')
                elif name=='rejected':
                    reply=await command('/reject_lunar '+decision_token);base.require('rejected' in reply,'Rejection failed')
                else:
                    reply=await command('/approve_lunar '+decision_token);base.require('scheduled' in reply,'Occurrence approval failed')
                if name=='cancelled':
                    reply=await command('/cancel_lunar '+occurrence)
                    reply=await command('/approve_lunar '+token(reply,'approve_lunar'))
                    base.require('Cancellation approved' in reply,'Reviewed cancellation failed')
            # HTTP body identity is never accepted as authority, even if it claims owner.
            with httpx.Client(transport=httpx.HTTPTransport(uds=self.config['service_socket']),trust_env=False) as client:
                bogus={'command':{'operation':'request','kind':'birthday','fixture':'success','user_id':101},'nonce':'forged','timestamp':int(time.time())}
                base.require(client.post('http://local/lunar',json=bogus,headers={'x-dincharya-signature':'0'*64}).status_code==403,'Unsigned forged identity accepted')
            print('PASS G02 actual SDK authorization, birthday/anniversary previews, separate approvals, replay/stale/reject/cancel',flush=True)
            pgid=self.compose('ps','-q','postgres-test').strip();started=self.inspect(pgid)['State']['StartedAt'];old_pid=self.service.pid
            await app.stop();await app.shutdown();self.stop_service();self.compose('restart','n8n-test',timeout=60)
            def ready():
                try:return self.compose('exec','-T','n8n-test','node','-e',"fetch('http://127.0.0.1:5678/healthz/readiness').then(r=>console.log(r.ok))").strip()=='true'
                except base.Failure:return False
            base.bounded_wait(ready,'n8n restart',timeout=60);self.start_service()
            base.require(self.service.pid!=old_pid,'Application process did not restart')
            app,wire=build(self.commands,self.ticks,interval=1);await app.initialize();await app.start()
            base.require(len(app.job_queue.jobs())==1,'Duplicate polling jobs')
            deadline=time.monotonic()+150
            while self.app_sql("SELECT count(*) FROM public.reminder_deliveries WHERE status IN ('sent','failed','uncertain')")!='4':
                base.require(time.monotonic()<deadline,'Automatic gateway polling did not complete delivery')
                await asyncio.sleep(.5)
            await app.stop()  # Settle the sole poller before inspecting failure backoff/cancel.
            states={}
            for name,occurrence in occurrences.items():
                state=await command('/lunar_status '+occurrence)
                states[name]=json.loads(state)
            for name,state in [('success','sent'),('anniversary','sent'),('failure','failed'),('uncertain','uncertain')]:
                row=states[name]['deliveries'][0];base.require(row['state']==state and row['attempts']==1,'Delivery state mismatch')
                base.require(row['has_receipt']==(state=='sent'),'Receipt mismatch')
            for name in ('stale','rejected'):base.require(states[name]['event_id'] is None,'Unapproved occurrence scheduled')
            base.require(states['cancelled']['cancelled'],'Cancellation not durable')
            base.require(self.app_sql('SELECT count(*) FROM synthetic_e2e.attempts')=='4','Duplicate simulated send')
            reply=await command('/cancel_lunar '+occurrences['failure']);await command('/approve_lunar '+token(reply,'approve_lunar'))
            print('PASS G03 automatic single gateway polling -> existing worker -> real Telegram adapter/simulated HTTP -> receipts/quarantine',flush=True)
            before=self.app_sql('SELECT json_agg(row_to_json(d) ORDER BY id) FROM public.reminder_deliveries d')
            await app.shutdown();self.stop_service();self.compose('restart','n8n-test',timeout=60);base.bounded_wait(ready,'second n8n restart',timeout=60);self.start_service()
            app,wire=build(self.commands,self.ticks,interval=1);await app.initialize();await app.start();await asyncio.sleep(4);await app.stop()
            base.require(self.app_sql('SELECT count(*) FROM synthetic_e2e.attempts')=='4','Restart resent reminder')
            base.require(self.app_sql('SELECT json_agg(row_to_json(d) ORDER BY id) FROM public.reminder_deliveries d')==before,'Restart changed delivery history')
            base.require(self.compose('ps','-q','postgres-test').strip()==pgid and self.inspect(pgid)['State']['StartedAt']==started,'PostgreSQL changed during restarts')
            with connection_factory(self.config['connections']['worker'])() as conn:
                try:conn.execute('SELECT lunar_api.delivery_status(%s)',(occurrences['success'],));raise AssertionError('Worker gained owner API')
                except Exception as error:
                    base.require(getattr(error,'sqlstate',None)=='42501','Unexpected worker privilege outcome')
            # Focused unchanged Gregorian path control; no full recurrence acceptance rerun.
            native=self.app_sql("SELECT public.propose_gregorian_change('add','series',NULL,NULL,jsonb_build_object('title','Synthetic Gregorian control','start_time','02:00','timezone','Asia/Kolkata','recurrence_rule',jsonb_build_object('calendar_system','gregorian','frequency','once','interval_count',1,'start_date',current_date+2)),101)")
            base.require(self.app_sql(f"SELECT success FROM public.decide_gregorian_change({native},101,'approve',true)")=='t','Gregorian regression')
            base.require(self.baseline.read_bytes()==self.original,'Schema source modified')
            print('PASS G04 real process/n8n/gateway restart, exact history, permissions and Gregorian control',flush=True)
        finally:
            if app.running:await app.stop()
            await app.shutdown()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path,required=True);parser.add_argument('--expected-daemon-id',required=True);parser.add_argument('--execute-approved',action='store_true');args=parser.parse_args()
    try:
        base.require(args.execute_approved,'Explicit isolated execution approval required')
        base.require(args.baseline.is_file() and not args.baseline.is_symlink(),'Exact regular schema required')
        M2GRunner.baseline=args.baseline;base.Runner=M2GRunner;base.execute(args.expected_daemon_id)
    except Exception as error:
        print(str(error) if isinstance(error,base.Failure) else 'M2G acceptance failed; private details suppressed',file=sys.stderr);return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
