"""Attended Stage 2 phase driver. Never configures Windows or initiates reboot."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.environ['DINCHARYA_STAGE2']='1'
from control import PROJECT,STATE,ROOT,compose,docker
from complete import SILENT,LOST,preview,evidence,slots,recorder,history,query,require,probe

DAEMON='44c1ef83-c50e-4ecc-8f19-4b112bc40f29'
PHASES=('prepare','arm','closed','interrupt','recover','verify','export')
JOURNAL=STATE/'physical'
ROLES=('db','relay','app','gateway','worker')


def phase_guard(journal,name):
    i=PHASES.index(name)
    require(all((journal/(p+'.done')).is_file() for p in PHASES[:i]),'missing checkpoint')
    with (journal/(name+'.started')).open('x') as f:
        f.write(str(time.time()))
        f.flush()
        os.fsync(f.fileno())


def save(name,value):
    with (JOURNAL/name).open('x') as f:
        json.dump(value,f)
        f.flush()
        os.fsync(f.fileno())


def read(name):
    return json.loads((JOURNAL/name).read_text())


def windows(script):
    return subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',
        "$ErrorActionPreference='Stop'; "+script],text=True,timeout=20).strip()


def boot():
    return int(windows('[DateTimeOffset]::new((Get-CimInstance Win32_OperatingSystem).LastBootUpTime).ToUnixTimeSeconds()'))


def ac():
    require(windows('Add-Type -AssemblyName System.Windows.Forms; [Windows.Forms.SystemInformation]::PowerStatus.PowerLineStatus')=='Online','AC unavailable')


def old_inventory():
    records=[]
    for name in ('dincharya-laptop-staging','dincharya-stage1-recheck','dincharya-stage1-complete'):
        label='label=com.docker.compose.project='+name
        containers=docker('ps','-a','--filter',label,'--format','{{.ID}} {{.State}}',capture_output=True,text=True).stdout.splitlines()
        volumes=docker('volume','ls','-q','--filter',label,capture_output=True,text=True).stdout.splitlines()
        require(len(containers)==5 and len(volumes)==4 and all(c.endswith(' exited') for c in containers),'prior project inventory')
        records.extend(sorted(containers)+sorted(volumes))
    return records


def validate_monitor(rows,closed,opened,stopped,recovered):
    samples=[(datetime.fromisoformat(r['utc']).timestamp(),r['state']) for r in rows]
    relevant=[(t,s) for t,s in samples if closed-30<=t<=recovered+60]
    require(len(relevant)>2 and all(0<b[0]-a[0]<=35 for a,b in zip(relevant,relevant[1:])),'observer continuity')
    lid=[(t,s) for t,s in relevant if closed<=t<=opened]
    require(opened-closed>=1800 and lid and lid[0][0]-closed<=30 and opened-lid[-1][0]<=30
            and all(s=='ready' for _,s in lid),'closed-lid samples')
    require(any(s=='outage' and stopped<=t<=recovered for t,s in relevant),'missing outage')
    require(any(s=='ready' and recovered<=t<=recovered+45 for t,s in relevant),'missing recovery')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('phase',choices=(*PHASES,'inspect','stop','status','open'))
    a=p.parse_args()
    phase=a.phase
    rev=os.environ['REV']
    pins=['--daemon',DAEMON,'--revision',rev]
    require(PROJECT=='dincharya-stage2-physical' and not any(k.startswith(('DOCKER_','COMPOSE_')) for k in os.environ),'context')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==rev and
            not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT),'checkout')
    if phase=='inspect':
        print(sorted(p.name for p in JOURNAL.glob('*.started')),sorted(p.name for p in JOURNAL.glob('*.done')),
              'aborted' if (JOURNAL/'aborted').exists() else 'inspect only')
        return
    require(docker('info','--format','{{.ID}}',capture_output=True,text=True).stdout.strip()==DAEMON,'daemon')
    def stage(action,*args):
        return subprocess.check_output([sys.executable,'-B',str(ROOT/'staging/laptop/control.py'),action,*pins,*args],text=True)
    if phase=='prepare':
        require(not STATE.exists(),'preserve existing Stage 2 state')
        require(not docker('network','ls','-q','--filter','name=^dincharya-stage2-physical_default$',capture_output=True).stdout.strip(),'network collision')
        prior=old_inventory()
        def image(role):
            ids=docker('ps','-aq','--filter','label=com.docker.compose.project=dincharya-stage1-complete',
                       '--filter','label=com.docker.compose.service='+role,capture_output=True,text=True).stdout.split()
            require(len(ids)==1,'accepted image unavailable')
            return docker('inspect','--format','{{.Image}}',ids[0],capture_output=True,text=True).stdout.strip()
        ac()
        stage('prepare','--app',image('app'),'--db',image('db'),'--relay',image('relay'),'--kernel',os.environ['KERNEL'])
        JOURNAL.mkdir(mode=0o700)
        phase_guard(JOURNAL,phase)
        save('prior',prior)
        stage('initialize')
        stage('start')
        probe(*pins)
    elif phase=='status':
        ac()
        print(json.dumps(dict(json.loads(stage('status')),project=PROJECT,revision=rev)))
        return
    elif phase=='stop':
        (JOURNAL/'aborted').touch()
        stage('stop')
        require(old_inventory()==read('prior'),'inventory changed')
        return
    elif (JOURNAL/'aborted').exists():
        raise RuntimeError('Aborted session; inspect only')
    elif phase=='open':
        require((JOURNAL/'closed.done').is_file() and not (JOURNAL/'interrupt.started').exists(),'open checkpoint')
        now=time.time()
        require(now-read('closed.done')>=1800,'lid interval too short')
        ac()
        start=int(read('closed.done'))
        count=windows(f"$s=[DateTimeOffset]::FromUnixTimeSeconds({start}).LocalDateTime; "
                      "Get-WinEvent -ListLog System -ErrorAction Stop | Out-Null; "
                      "try { @(Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='Microsoft-Windows-Kernel-Power';"
                      "StartTime=$s;Id=42,506} -ErrorAction Stop).Count } catch { "
                      "if ($_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*'){0}else{throw} }")
        require(count=='0' and boot()==read('boot'),'sleep or unexpected boot')
        save('opened',now)
        return
    else:
        phase_guard(JOURNAL,phase)
        if phase=='arm':
            ac()
            t=int(time.time()//60)*60
            due={name:t+offset*60 for name,offset in [('Stage First',5),('Stage Second',20),('Stage Outage',35),('Stage Recovered',45),(LOST,47)]}
            require(query('SELECT count(*) FROM public.schedule_events')=='0' and recorder()==[],'dirty project')
            save('due',due)
            save('boot',boot())
            for i,(name,when) in enumerate([(SILENT,t+180),*due.items()],1):
                answer=preview(i,name,when)(1)
                control=query(f"SELECT c.id FROM lunar_private.recurring_control c JOIN public.schedule_events e ON e.id=c.event_id WHERE e.title='{name}'")
                require(control and answer['messages']==[f'Rule approved. ID {control}.'] and
                        answer['keyboard'] is None and answer['relay']=='approved_reply','approval mismatch')
            print('Close now; open after 30 full minutes. Outage due (UTC epoch):',due['Stage Outage'])
        elif phase=='closed':
            ac()
            require(time.time()<read('due')['Stage First']-120,'missed lid window')
        elif phase=='interrupt':
            require((JOURNAL/'opened').is_file(),'physical lid evidence missing')
            due=read('due')
            evidence(slots(),recorder(),due,{'Stage First','Stage Second'})
            require(time.time()<due['Stage Outage']-30,'missed reboot window')
            stage('stop')
            require(time.time()<due['Stage Outage'],'late stop')
        elif phase=='recover':
            due=read('due')
            ac()
            require(boot()>read('boot') and due['Stage Outage']<=time.time()<due['Stage Outage']+150,'reboot/login window')
            require(not compose('ps','--status','running','-q',capture_output=True).stdout.strip(),'unexpected pre-login activation')
            save('recovery-start',time.time())
            stage('start')
            probe(*pins)
        elif phase=='verify':
            due=read('due')
            require(time.time()>=due[LOST]+20,'wait for subsequent worker ticks')
            attempts=recorder()
            evidence(slots(),attempts,due,set(due))
            require(next(row[3] for row in attempts if row[2]=='Stage Outage')>=read('recovery-start'),'premature catch-up')
            time.sleep(12)
            require(recorder()==attempts,'unexpected repeat after worker ticks')
            require(json.loads(probe(*pins).stdout)['uncertain']==1,'quarantine health')
            require(query('SELECT count(*) FROM public.schedule_events')=='6','event count')
            # Check the accepted database lock held by the one running worker.
            require(len(compose('ps','-q','worker',capture_output=True,text=True).stdout.split())==1 and
                    query("SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND classid=20261112 AND objid=3 AND granted")=='1','single worker')
            monitor=[json.loads(line) for line in Path(os.environ['OBSERVER_LOG']).read_text().splitlines()]
            require(all(row.get('revision')==rev for row in monitor),'wrong observer log')
            validate_monitor(monitor,read('closed.done'),read('opened'),read('interrupt.done'),read('recover.done'))
            compose('stop','-t','40','gateway','worker','app',capture_output=True)
            save('history',history(query))
        elif phase=='export':
            require(os.environ.get('APPROVED_STAGE2_EXPORT')==rev,'explicit transfer scope required')
            dest=Path(os.environ['OFFHOST']).resolve(strict=True)
            source=subprocess.check_output(['findmnt','-n','-T',str(dest),'-o','SOURCE'],text=True).strip()
            require(source==os.environ['APPROVED_MOUNT_SOURCE'],'wrong backup destination')
            out=json.loads(stage('backup','--recipient',os.environ['CERT_SHA256'],'--certificate',os.environ['CERT'],'--destination',str(dest)))
            manifest=dict(revision=rev,digest=out['backup_sha256'],history=read('history'))
            save('restore-manifest',manifest)
            stage('stop')
            require(old_inventory()==read('prior'),'prior inventory changed')
    save(phase+'.done',time.time())
    print('PASS',phase)


if __name__=='__main__':
    main()
