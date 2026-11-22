"""One-use Stage 1 timed integration on an independent, synthetic project."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from zoneinfo import ZoneInfo

from confirmation import snapshot, verify_confirmation
from control import DB, PROJECT, STATE, compose, docker, encrypt_command, sql
from journey import query
from recheck import inject
from restore import restore

SILENT, FIRST, LOST, SECOND = ('Staging Silent','Staging First','Staging uncertain','Staging Second')
TABLES=('public.schedule_events','lunar_private.recurring_control','lunar_private.recurring_audit',
        'lunar_private.notification_policy','lunar_private.notification_slot','public.reminder_deliveries')
OWNER={'id':101,'is_bot':False,'first_name':'Synthetic'}


def require(ok, label):
    if not ok:
        raise RuntimeError(label)


def history(read):
    # Stable row hashes include keys, receipt pairs, policy, attempts and audit snapshots.
    return [read(f"SELECT encode(sha256(convert_to(coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)),'[]')::text,'UTF8')),'hex') FROM {table} t") for table in TABLES]


def preview(n,title,due):
    local=datetime.fromtimestamp(due,ZoneInfo('Asia/Kolkata'))
    policy='none' if title==SILENT else 'at start'
    msg=dict(message_id=n,date=int(time.time()),chat={'id':101,'type':'private'},
             text=f'Schedule {title} on {local:%Y-%m-%d} at {local:%H:%M}; {policy}')
    answer=inject({'update_id':10*n,'message':{**msg,'from':OWNER}})
    markup=answer['keyboard']
    if isinstance(markup,str):
        markup=json.loads(markup)
    ticket=markup['inline_keyboard'][0][0]['callback_data']
    require(len(answer['messages'])==1 and ticket.startswith('lunar:confirm:'),'preview')
    def click(offset, actor=OWNER):
        number=10*n+offset
        return inject({'update_id':number,'callback_query':{'id':str(number),'from':actor,'data':ticket,
                       'message':msg,'chat_instance':'synthetic'}})
    return click


def recorder():
    code="""import sqlite3,json
db=sqlite3.connect('file:/record/attempts.sqlite?mode=ro',uri=True)
count=db.execute('SELECT count(*) FROM attempts').fetchone()[0]
rows=db.execute('SELECT a.id,a.uncertain,o.title,o.utc FROM attempts a LEFT JOIN observed o USING(id) ORDER BY a.id').fetchall() if count else []
print(json.dumps(rows))"""
    return json.loads(compose('exec','-T','worker','python','-c',code,capture_output=True,text=True,timeout=10).stdout)


def slots():
    return json.loads(query("""SELECT coalesce(jsonb_agg(jsonb_build_array(e.title,s.status,s.attempts,
        s.telegram_chat_id,s.telegram_message_id,extract(epoch FROM s.due_at)) ORDER BY s.id),'[]')
        FROM lunar_private.notification_slot s JOIN public.schedule_events e ON e.id=s.event_id"""))


def evidence(rows, attempts, due, completed):
    require(len(rows)==len(due) and {r[0] for r in rows}==set(due),'unexpected slot')
    require(len(attempts)==len(completed) and {r[2] for r in attempts}==set(completed),'unexpected send')
    require(len({r[0] for r in attempts})==len(attempts),'duplicate recorder identity')
    by_title={r[2]:r for r in attempts}
    for title,status,count,chat,receipt,epoch in rows:
        require(epoch==due[title],'incorrect civil due time')
        if title not in completed:
            require((status,count,chat,receipt)==('pending',0,None,None),'premature claim')
            continue
        mid,uncertain,_,when=by_title[title]
        require(due[title]<=when<=due[title]+180,'delivery outside timed window')
        expected=('uncertain',1,None,None) if title==LOST else ('sent',1,101,mid)
        require(uncertain==int(title==LOST) and (status,count,chat,receipt)==expected,'receipt mismatch')


def at(epoch):
    remaining=epoch-time.time()
    if remaining>0:
        time.sleep(remaining)


def await_outcome(title,deadline):
    while time.time()<deadline:
        if any(r[0]==title and r[1] in ('sent','uncertain') for r in slots()):
            return
        time.sleep(2)
    raise RuntimeError('Timed outcome missing')


def probe(*pins):
    return subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('control.py')),'status',*pins],
                          check=True,capture_output=True,text=True,timeout=45)


def dump_restore(pg,daemon):
    # Quiesced source. Only this disposable project may enter this helper.
    before=history(query)
    with tempfile.TemporaryDirectory() as tmp:
        key,cert,archive=[Path(tmp)/n for n in ('key','cert','archive')]
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-noenc','-subj','/CN=Stage1',
                        '-days','1','-keyout',key,'-out',cert],check=True,capture_output=True)
        der=subprocess.check_output(['openssl','x509','-in',cert,'-outform','DER'])
        with subprocess.Popen(encrypt_command(hashlib.sha256(der).hexdigest(),cert,archive),stdin=subprocess.PIPE) as enc:
            try:
                sql('pg_dump','-Fc','-U','synthetic_test','-d',DB,stdout=enc.stdin)
            finally:
                enc.stdin.close()
            require(enc.wait()==0,'dump encryption')
        with archive.open('rb') as stream:
            digest=hashlib.file_digest(stream,'sha256').hexdigest()
        restore(archive,key,digest,pg,daemon,verify=lambda read:require(history(read)==before,'restore history'))


def run(revision,daemon,pg):
    require(PROJECT=='dincharya-stage1-complete','namespace')
    pins=('--revision',revision,'--daemon',daemon)
    probe(*pins)
    network=PROJECT+'_default'
    require(docker('network','inspect','--format','{{.Internal}}',network,capture_output=True,text=True).stdout.strip()=='true','internal network')
    for role in ('db','relay','app','gateway','worker'):
        ids=compose('ps','-q',role,capture_output=True,text=True).stdout.split()
        require(len(ids)==1,'service cardinality')
        fmt='{{json .NetworkSettings.Networks}}'
        networks=json.loads(docker('inspect','--format',fmt,ids[0],capture_output=True,text=True).stdout)
        require(set(networks)=={network},'unexpected network')
        bindings=docker('inspect','--format','{{json .HostConfig.PortBindings}}',ids[0],capture_output=True,text=True).stdout
        require(not json.loads(bindings),'published port')
    with (STATE/'complete.started').open('x') as f:
        f.write('reserved')
    require(snapshot(query)==([0]*5,None) and not recorder(),'fresh fixture')
    # Use actual wall time. The final slot falls due while the worker is stopped.
    t=int(time.time()//60)*60+180
    due={FIRST:t,LOST:t+60,SECOND:t+180}
    first=preview(1,SILENT,t-60)
    require(first(1,{**OWNER,'id':202})['messages']==[] and snapshot(query)==([0]*5,None),'foreign decision')
    verify_confirmation(first(2),lambda:snapshot(query))
    initial=snapshot(query)
    verify_confirmation(first(3),lambda:snapshot(query))
    require(snapshot(query)==initial and not recorder(),'changed duplicate')
    for n,(title,epoch) in enumerate(due.items(),2):
        reply=preview(n,title,epoch)(1)
        control=query(f"SELECT c.id FROM lunar_private.recurring_control c JOIN public.schedule_events e ON e.id=c.event_id WHERE e.title='{title}'")
        require(control and reply['messages']==[f'Rule approved. ID {control}.'] and reply['keyboard'] is None,'approval')
    stale=preview(5,'Staging Stale',t+900)
    require(time.time()<t,'setup missed timing')
    try:
        compose('run','--rm','--no-deps','-T','worker',capture_output=True,timeout=25)
    except subprocess.CalledProcessError as err:
        require(err.returncode==75,'competing worker failed for wrong reason')
    else:
        raise RuntimeError('Competing worker admitted')
    await_outcome(FIRST,t+45)
    evidence(slots(),recorder(),due,{FIRST})
    await_outcome(LOST,t+105)
    evidence(slots(),recorder(),due,{FIRST,LOST})
    require(json.loads(probe(*pins).stdout)['uncertain']==1,'quarantine health')
    before=history(query)
    previous_attempts=recorder()
    compose('stop','-t','25','gateway','worker','app',capture_output=True,timeout=90)
    try:
        probe(*pins)
    except subprocess.CalledProcessError:
        pass
    else:
        raise RuntimeError('Health failed to detect outage')
    require(time.time()<due[SECOND],'outage missed due time')
    at(due[SECOND]+2)
    require(history(query)==before,'history changed during outage')
    compose('up','-d','--pull','never','--wait','--wait-timeout','100',capture_output=True)
    await_outcome(SECOND,due[SECOND]+180)
    finished=history(query)
    require(finished[:4]==before[:4] and previous_attempts==recorder()[:2],'restart lost durable history')
    denied=stale(2)
    require(denied['relay']=='unexpected_result' and len(denied['messages'])==1 and
            'preview_expired_or_unavailable' in denied['messages'][0] and denied['keyboard'] is None,'stale approval')
    time.sleep(12)
    require(history(query)==finished and snapshot(query)[0]==[4,4,4,3,0],'replay or stale write')
    evidence(slots(),recorder(),due,set(due))
    h=json.loads(probe(*pins).stdout)
    require(h==dict(relay='ready',due=0,uncertain=1,dead=0,sending=0),'recovery health')
    print('PASS timed paired receipts=2, silent attempts=0, uncertain attempts=1, competing worker excluded, restart and stale review',flush=True)
    compose('stop','-t','25','gateway','worker','app',capture_output=True,timeout=90)
    dump_restore(pg,daemon)
    print('PASS local encrypted PostgreSQL dump and networkless restore; six history tables matched',flush=True)


if __name__=='__main__':
    run(*sys.argv[1:])
