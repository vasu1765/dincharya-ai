"""One fresh recovery-only session. Never reboot Windows or resume aborted physical state."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

os.environ['DINCHARYA_STAGE2_RECOVERY_ONLY'] = '1'
from control import ROOT, STATE, PROJECT, DB, docker, compose, encrypt_command, sql
from complete import SILENT, LOST, preview, query, history, slots, recorder, probe, await_outcome
from recovery_checks import PHASES, OVERDUE, next_phase, performance, evidence, observer_evidence, require

DAEMON = '44c1ef83-c50e-4ecc-8f19-4b112bc40f29'
PRIOR = ('dincharya-laptop-staging','dincharya-stage1-recheck',
         'dincharya-stage1-complete','dincharya-stage2-physical')
JOURNAL = STATE/'recovery'


def save(name, value):
    with (JOURNAL/name).open('x') as f:
        json.dump(value,f); f.flush(); os.fsync(f.fileno())
    fd=os.open(JOURNAL,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def read(name):
    return json.loads((JOURNAL/name).read_text())


def windows(script):
    return subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',
        "$ErrorActionPreference='Stop'; "+script],text=True,timeout=20).strip()


def boot():
    return int(windows('[DateTimeOffset]::new((Get-CimInstance Win32_OperatingSystem).LastBootUpTime).ToUnixTimeSeconds()'))


def ac():
    require(windows('Add-Type -AssemblyName System.Windows.Forms; [Windows.Forms.SystemInformation]::PowerStatus.PowerLineStatus')=='Online','AC unavailable')


def inventory():
    result={}
    for project in PRIOR:
        label='label=com.docker.compose.project='+project
        ids=docker('ps','-aq','--filter',label,capture_output=True,text=True).stdout.split()
        require(len(ids)==5,'prior container count')
        rows=json.loads(docker('inspect',*ids,capture_output=True,text=True).stdout)
        require(all(r['State']['Status']=='exited' for r in rows),'prior project running')
        volumes=sorted(docker('volume','ls','-q','--filter',label,capture_output=True,text=True).stdout.split())
        require(len(volumes)==4,'prior volume count')
        result[project]={'containers': sorted([r['Id'],r['State']['Status'],r['State']['StartedAt'],r['State']['FinishedAt'],r['RestartCount']] for r in rows), 'volumes':volumes}
    # Never read credentials, backup payloads, database volume files or recorder DBs.
    old=Path.home()/'.local/state/dincharya-stage2-physical/physical'
    require((old/'aborted').is_file(),'aborted session must remain aborted')
    result['aborted_journal']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
        for p in old.iterdir() if p.is_file() and not p.is_symlink()}
    return result


def stage(action,*args):
    return subprocess.check_output([sys.executable,'-B',str(ROOT/'staging/laptop/control.py'),action,
        '--daemon',DAEMON,'--revision',os.environ['REV'],*args],text=True,stderr=subprocess.DEVNULL)


def reserve(phase):
    started={p.stem for p in JOURNAL.glob('*.started')}
    done={p.stem for p in JOURNAL.glob('*.done')}
    require(next_phase(started,done)==phase,'phase order')
    save(phase+'.started',time.time())


def wait_until(epoch):
    while time.time()<epoch:
        time.sleep(min(5,epoch-time.time()))


def export_usb():
    cert=Path(os.environ['CERT']); pin=os.environ['CERT_SHA256']
    parent=Path(os.environ['USB_STAGING_PARENT'])
    require(parent.is_dir() and not parent.is_symlink() and parent.stat().st_uid==os.getuid()
            and parent.stat().st_mode & 0o077==0,'private local export parent')
    destination=parent/'recovery-only-usb-export'
    require(not destination.exists() and not destination.is_symlink(),'preserve export')
    require(cert.is_file() and not cert.is_symlink(),'certificate')
    subprocess.run(['openssl','x509','-in',str(cert),'-checkend','3600','-noout'],check=True,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    encrypt_command(pin,cert,parent/'unused-not-created')
    require(history(query)==read('history'),'quiesced history changed')
    for role in ('app','gateway','worker'):
        require(not compose('ps','--status','running','-q',role,capture_output=True).stdout.strip(),'writers running')
    require({'certificate':str(cert.resolve()),'fingerprint':pin}==read('recipient'),'approved recipient changed')
    fs=subprocess.check_output(['findmnt','-T',str(parent),'-n','-o','FSTYPE'],text=True).strip()
    require(fs=='ext4','local Linux export staging required')
    reserve('export')
    destination.mkdir(mode=0o700)
    with tempfile.TemporaryDirectory(dir=destination) as tmp:
        path=Path(tmp)/'encrypted'
        with subprocess.Popen(encrypt_command(pin,cert,path),stdin=subprocess.PIPE,
                              stderr=subprocess.DEVNULL) as enc:
            try: sql('pg_dump','-Fc','-U','synthetic_test','-d',DB,stdout=enc.stdin,stderr=subprocess.DEVNULL)
            finally: enc.stdin.close()
            require(enc.wait()==0,'encryption')
        with path.open('rb') as f:
            os.fsync(f.fileno()); digest=hashlib.file_digest(f,'sha256').hexdigest()
        os.link(path,destination/(digest+'.dump.cms'))
    require(history(query)==read('history'),'export history changed')
    manifest=dict(revision=os.environ['REV'],digest=digest,history=read('history'))
    save('restore-manifest',manifest)
    raw=(JOURNAL/'restore-manifest').read_bytes()
    with (destination/'restore-manifest').open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
    fd=os.open(destination,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
    stage('stop')
    require(inventory()==read('prior'),'prior inventories changed')
    save('export.done',time.time())
    print('PASS encrypted export and scoped stop; owner USB transfer/ThinkPad restore PENDING',flush=True)
    print('Ciphertext SHA-256:',digest,flush=True)
    print('Manifest SHA-256:',hashlib.sha256(raw).hexdigest(),flush=True)


def run(action="run"):
    revision=os.environ['REV']
    require(PROJECT=='dincharya-stage2-recovery-only','namespace')
    require(not any(k.startswith(('DOCKER_','COMPOSE_')) for k in os.environ),'ambient override')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==revision
            and not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT),'clean reviewed checkout')
    require(docker('info','--format','{{.ID}}',capture_output=True,text=True).stdout.strip()==DAEMON,'daemon')
    ac()
    if action=='status':
        print(json.dumps(dict(json.loads(stage('status')),project=PROJECT,revision=revision)))
        return
    if action=='inspect':
        print(json.dumps({'started':sorted(p.stem for p in JOURNAL.glob('*.started')),
                          'done':sorted(p.stem for p in JOURNAL.glob('*.done')),
                          'aborted':(JOURNAL/'aborted').exists()}))
        return
    if action=='stop':
        require(JOURNAL.is_dir(),'no initialized session')
        stop_lock=(JOURNAL/'session.lock').open('a')
        fcntl.flock(stop_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        (JOURNAL/'aborted').touch(exist_ok=False)
        stage('stop')
        require(inventory()==read('prior'),'prior inventories changed')
        print('PASS scoped recovery-only stop; state preserved')
        return
    if not JOURNAL.exists():
        require(not STATE.exists(),'preserve existing state')
        prior=inventory()
        cert=Path(os.environ['CERT']);pin=os.environ['CERT_SHA256']
        require(cert.is_file() and not cert.is_symlink(),'public recipient certificate')
        encrypt_command(pin,cert,STATE/'unused-not-created')
        subprocess.run(['openssl','x509','-in',str(cert),'-checkend','7200','-noout'],check=True,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        # Reserve outside the controller-created STATE; never replay partial preparation.
        guard=STATE.with_name(STATE.name+'.prepare-reserved')
        with guard.open('x') as f: f.write(revision); f.flush(); os.fsync(f.fileno())
        def image(role):
            ids=docker('ps','-aq','--filter','label=com.docker.compose.project=dincharya-stage1-complete',
                '--filter','label=com.docker.compose.service='+role,capture_output=True,text=True).stdout.split()
            require(len(ids)==1,'accepted image')
            return docker('inspect','--format','{{.Image}}',ids[0],capture_output=True,text=True).stdout.strip()
        stage('prepare','--app',image('app'),'--db',image('db'),'--relay',image('relay'),'--kernel',os.environ['KERNEL'])
        JOURNAL.mkdir(mode=0o700)
        reserve('prepare'); save('prior',prior)
        save('recipient',{'certificate':str(cert.resolve()),'fingerprint':pin})
        stage('initialize'); stage('start')
        probe('--daemon',DAEMON,'--revision',revision)
        save('prepare.done',time.time())
        print('PASS fresh preparation; NOT ARMED. Configure exact-target observer and fresh readiness before re-running.',flush=True)
        return
    lock=(JOURNAL/'session.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    require(not (JOURNAL/'aborted').exists(),'aborted session')
    require(inventory()==read('prior'),'preserved inventory changed')
    while True:
        require(not (JOURNAL/'aborted').exists(),'aborted session')
        phase=next_phase({p.stem for p in JOURNAL.glob('*.started')},{p.stem for p in JOURNAL.glob('*.done')})
        if phase is None:
            passed=read('performance')['within_600_seconds']
            print(('PASS' if passed else 'FAIL')+' source startup performance; functional delivery/export complete; independent USB restore still pending',flush=True)
            if not passed: raise SystemExit(2)
            return
        if phase=='arm':
            stamp=float(os.environ.get('OWNER_OBSERVER_READY_UTC','0'))
            require(os.environ.get('OWNER_ATTENDING')=='1' and 0<=time.time()-stamp<=45,'fresh owner/observer readiness')
            require(query('SELECT count(*) FROM public.schedule_events')=='0' and recorder()==[],'fresh fixture')
            reserve(phase)
            t=int(time.time()//60)*60+60
            due={'Recovery First':t+60,'Recovery Outage A':t+180,'Recovery Outage B':t+240,
                 'Recovery After':t+960,LOST:t+1020}
            save('due',due); save('boot',boot())
            for i,(title,when) in enumerate([(SILENT,t+120),*due.items()],1):
                reply=preview(i,title,when)(1)
                control=query(f"SELECT c.id FROM lunar_private.recurring_control c JOIN public.schedule_events e ON e.id=c.event_id WHERE e.title='{title}'")
                require(control and reply['messages']==[f'Rule approved. ID {control}.']
                        and reply['keyboard'] is None and reply['relay']=='approved_reply','approval mismatch')
            require(time.time()<due['Recovery First'],'fixture setup missed due time')
        elif phase=='interrupt':
            await_outcome('Recovery First',read('due')['Recovery First']+100)
            evidence(slots(),recorder(),read('due'),{'Recovery First'})
            require(time.time()<read('due')['Recovery Outage A']-20,'interrupt window')
            reserve(phase)
            save('pre-attempts',recorder());save('pre-static',history(query)[:4])
            stage('stop')
            save('interrupt.done',time.time())
            from datetime import datetime
            from zoneinfo import ZoneInfo
            login=read('due')['Recovery Outage B']
            print('PASS interruption. OWNER: reboot once now; stay at login through '+
                datetime.fromtimestamp(login,ZoneInfo('Asia/Kolkata')).isoformat()+
                '; then log in/start Docker, WSL and attended bridge manually; rerun same task.',flush=True)
            print('Stop-to-ready performance target UTC epoch:',read('interrupt.done')+600,flush=True)
            return
        elif phase=='recover':
            due=read('due')
            require(boot()>read('boot'),'Windows reboot evidence')
            require(max(due[n] for n in OVERDUE)<=time.time()<min(due[n] for n in OVERDUE)+21000,'safe functional recovery window')
            require(not compose('ps','--status','running','-q',capture_output=True).stdout.strip(),'unexpected pre-recovery activation')
            reserve(phase);save('recovery-start',time.time())
            stage('start');probe('--daemon',DAEMON,'--revision',revision)
            ready=time.time();save('ready',ready);save('performance',performance(read('interrupt.done'),ready))
            for title in OVERDUE: await_outcome(title,ready+120)
            evidence(slots(),recorder(),due,{'Recovery First',*OVERDUE},ready,read('interrupt.done'),read('recovery-start'))
            recovered=[r for r in recorder() if r[2] in OVERDUE]
            save('catchup-timing',{'stop_to_first_receipt_seconds':min(r[3] for r in recovered)-read('interrupt.done'),
                 'overdue_seconds':{r[2]:r[3]-due[r[2]] for r in recovered},
                 'ready_to_last_receipt_seconds':max(r[3] for r in recovered)-ready})
            require(history(query)[:4]==read('pre-static') and recorder()[0]==read('pre-attempts')[0],'lost pre-outage history')
        elif phase=='verify':
            # Wait before reservation. Missing observer log is a safe resumable checkpoint.
            wait_until(read('due')[LOST]+25)
            log=os.environ.get('OBSERVER_LOG')
            if not log or not Path(log).is_file():
                print('WAIT observer JSONL copy to Acer; rerun same task with OBSERVER_LOG; no verify phase reserved',flush=True)
                return
            rows=[json.loads(x) for x in Path(log).read_text().splitlines()]
            observer_evidence(rows,revision,read('arm.done'),read('interrupt.done'),read('ready'))
            reserve(phase)
            evidence(slots(),recorder(),read('due'),set(read('due')),read('ready'),read('interrupt.done'),read('recovery-start'))
            require(query('SELECT count(*) FROM public.schedule_events')=='6' and query('SELECT count(*) FROM public.reminder_deliveries')=='0','silent/legacy work')
            require(query('SELECT count(*) FROM lunar_private.notification_slot WHERE lease_until IS NOT NULL OR worker_token IS NOT NULL')=='0','resolved slot retains lease')
            before=history(query);attempts=recorder()
            require(len(compose('ps','-q','worker',capture_output=True,text=True).stdout.split())==1,'worker cardinality')
            require(query("SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND classid=20261112 AND objid=3 AND granted")=='1','worker lock')
            try: compose('run','--rm','--no-deps','-T','worker',capture_output=True,timeout=25)
            except subprocess.CalledProcessError as e: require(e.returncode==75,'competing worker exit')
            else: raise ValueError('competing worker admitted')
            compose('stop','-t','40','app','worker',capture_output=True)
            compose('up','-d','--pull','never','--wait','--wait-timeout','120','app','worker',capture_output=True)
            time.sleep(12)
            require(history(query)==before and recorder()==attempts,'restart duplicated or changed history')
            require(len(compose('ps','-q','worker',capture_output=True,text=True).stdout.split())==1 and
                    query("SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND classid=20261112 AND objid=3 AND granted")=='1','restart worker ownership')
            health=json.loads(probe('--daemon',DAEMON,'--revision',revision).stdout)
            require(health==dict(relay='ready',due=0,uncertain=1,dead=0,sending=0),'quarantine health')
            compose('stop','-t','40','gateway','app','worker',capture_output=True)
            save('history',history(query))
            save('functional',{'paired_receipts':4,'uncertain_attempts':1,'silent_attempts':0,'duplicate_attempts':0})
        elif phase=='export':
            if os.environ.get('APPROVED_STAGE2_USB_EXPORT')!=revision:
                print('WAIT explicit USB export flag and pinned certificate inputs; no export reserved',flush=True)
                return
            export_usb(); continue
        else: raise ValueError('invalid phase')
        save(phase+'.done',time.time())
        print('PASS functional phase '+phase,flush=True)
        if phase=='recover':
            print(('PASS' if read('performance')['within_600_seconds'] else 'FAIL')+' 600-second startup performance; functional result is separate',flush=True)


if __name__=='__main__':
    try:
        os.umask(0o077)
        parser=argparse.ArgumentParser()
        parser.add_argument("action",choices=("run","status","inspect","stop"),nargs="?",default="run")
        run(parser.parse_args().action)
    except Exception:
        print('FAIL recovery-only task; inspect durable stage; never replay an uncertain phase',file=sys.stderr)
        sys.exit(1)
