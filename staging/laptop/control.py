"""Disposable Linux staging controller. Run from the reviewed Git checkout."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import time
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'staging/laptop'
PROJECT = 'dincharya-laptop-staging'
STATE = Path.home() / '.local/state' / PROJECT
DB = 'dincharya_app_test'
sys.path.insert(0, str(ROOT))


def cmd(args, **kw):
    return subprocess.run(args, check=True, **kw)


def definition(images):
    services = {}
    for role in ('app', 'gateway', 'worker'):
        mounts = [f'{STATE}/{role}.json:/cfg.json:ro']
        if role != 'gateway':
            mounts += ['socket:/var/run/postgresql']
        if role == 'app':
            mounts += [f'{STATE}/de440s.bsp:/public.bsp:ro']
        if role == 'worker':
            mounts += ['recorder:/record']
        services[role] = dict(image=images['app'], entrypoint=['/opt/application/bin/python' if role in ('app','worker') else 'python', '/src/staging/laptop/service.py', role],
                              volumes=mounts, healthcheck=dict(test=['CMD','python','/src/staging/laptop/service.py','health'],
                              interval='10s',timeout='3s',retries=3), init=True, stop_grace_period='40s')
    services['db'] = dict(image=images['db'], environment=dict(POSTGRES_USER='synthetic_test',POSTGRES_DB=DB,
        POSTGRES_PASSWORD_FILE='/run/pass',POSTGRES_INITDB_ARGS='--auth-local=scram-sha-256'),
        command=['postgres','-c','listen_addresses=','-c','log_min_error_statement=panic'],
        volumes=['data:/var/lib/postgresql/data','socket:/var/run/postgresql',f'{STATE}/pass:/run/pass:ro'],
        healthcheck=dict(test=['CMD-SHELL','test "$(cat /proc/1/comm)" = postgres && pg_isready -U synthetic_test -d dincharya_app_test'],interval='5s',timeout='3s',retries=6))
    services['relay'] = dict(image=images['relay'],volumes=['relay:/home/node/.n8n'],
        environment=dict(N8N_DIAGNOSTICS_ENABLED='false', N8N_VERSION_NOTIFICATIONS_ENABLED='false',
        N8N_SECURE_COOKIE='false',EXECUTIONS_DATA_SAVE_ON_SUCCESS='none',EXECUTIONS_DATA_SAVE_ON_ERROR='none',
        EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS='false',N8N_BLOCK_ENV_ACCESS_IN_NODE='true'))
    for name in ('app','gateway','worker'):
        services[name]['depends_on']={'db':{'condition':'service_healthy'}}
    services['gateway']['depends_on'].update(app={'condition':'service_healthy'},relay={'condition':'service_started'})
    for service in services.values():
        service['restart']='on-failure:3'
        service['logging']={'driver':'local','options':{'max-size':'2m','max-file':'2'}}
    return dict(name=PROJECT,services=services,networks={'default':{'internal':True}},
                volumes={v:{} for v in ('data','socket','relay','recorder')})

def docker(*args, **kw):
    return cmd(['docker',*args], **kw)

def compose(*args, **kw):
    return docker('compose','--env-file','/dev/null','-p',PROJECT,'-f',str(STATE/'compose.json'),*args,**kw)

def write(name, data):
    with (STATE/name).open('x') as out:
        out.write(data)

def validate_transfer(a):
    ticket=Path(a.ticket).read_bytes()
    if len(ticket)>4096:
        raise ValueError('Invalid handover')
    public=Path(a.authority).read_bytes()
    if hashlib.sha256(public).hexdigest()!=a.authority_sha:
        raise ValueError('Owner authority mismatch')
    cmd(['openssl','dgst','-sha256','-verify',a.authority,'-signature',a.signature],input=ticket,capture_output=True)
    value=json.loads(ticket)
    if (set(value)!={'source','destination','revision','fenced_at','project'} or
        value['project']!=PROJECT or value['destination']!=a.daemon or value['source']==a.daemon or
        value['revision']!=a.revision or not 0<=time.time()-value['fenced_at']<=3600):
        raise ValueError('Handover scope mismatch')

def prepare(a):
    from database.migrate import render_migrations
    from prototypes.panchang.guarded import development_profile
    import shutil
    from psycopg import sql as pgsql
    if docker('ps','-aq','--filter','label=com.docker.compose.project='+PROJECT,capture_output=True).stdout.strip() or docker('volume','ls','-q','--filter','label=com.docker.compose.project='+PROJECT,capture_output=True).stdout.strip():
        raise ValueError('existing project')
    for name in definition(dict(app='',db='',relay=''))['volumes']:
        check=subprocess.run(['docker','volume','inspect',PROJECT+'_'+name],capture_output=True)
        if check.returncode==0:
            raise ValueError('Staging volume already exists')
    images = {}
    for role in ('app','db','relay'):
        ref = getattr(a,role)
        digest = docker('image','inspect','--format','{{.Id}}',ref,capture_output=True,text=True).stdout.strip()
        if ref != digest:
            raise ValueError('full local image ID required')
        images[role] = ref
    kernel = Path(a.kernel)
    if hashlib.sha256(kernel.read_bytes()).hexdigest() != json.loads((ROOT/'prototypes/panchang/ephemeris.json').read_text())['sha256']:
        raise ValueError('kernel mismatch')
    for role,entry,version in [('db','postgres',' 17.'),('relay','n8n','2.47.3')]:
        output=docker('run','--rm','--network','none','--pull','never','--entrypoint',entry,images[role],'--version',capture_output=True,text=True).stdout.strip()
        if (role=='db' and version not in output) or (role=='relay' and output!=version):
            raise ValueError('image version mismatch')
    STATE.mkdir(mode=0o700,parents=True,exist_ok=False)
    shutil.copyfile(kernel, STATE/'de440s.bsp')
    os.chmod(STATE/'de440s.bsp',0o444)
    write('pass', secrets.token_hex(32))
    # The postgres image reads this as its own UID; parent directory is mode 0700.
    os.chmod(STATE/'pass',0o444)
    paths = sorted((ROOT/'database/migrations').glob('*.sql'))
    if [p.name[:4] for p in paths] != [f'{i:04d}' for i in range(1,15)]:
        raise ValueError('migration set changed')
    script = [(ROOT/'tests/integration/m2h_development_schema.sql').read_text(), render_migrations(paths),'BEGIN;']
    roles = {}
    for kind,group in [('owner','dincharya_lunar_owner'),('calculator','dincharya_lunar_calculator'),('worker','dincharya_reminder_worker')]:
        user = 'stage_'+kind
        phrase = secrets.token_hex(32)
        script.append(pgsql.SQL("CREATE ROLE {} LOGIN PASSWORD {}; GRANT {} TO {};").format(
            pgsql.Identifier(user),pgsql.Literal(phrase),pgsql.Identifier(group),pgsql.Identifier(user)).as_string())
        roles[kind] = dict(host='/var/run/postgresql',port=5432,dbname=DB,user=user)
        roles[kind]['password'] = phrase
        if kind != 'worker':
            script += [f"INSERT INTO lunar_private.principals SELECT oid,rolname,101,'{kind}',true FROM pg_roles WHERE rolname='{user}';"]
    profile = json.dumps(development_profile()).replace("'","''")
    script += [f"INSERT INTO lunar_private.profiles SELECT lunar_private.hash(v),v,true FROM (SELECT '{profile}'::jsonb v) p;",'COMMIT;']
    write('init.sql','\n'.join(script))
    key = secrets.token_hex(32)
    write('app.json',json.dumps(dict(development_astronomy=True,development_recurring=True,development_historical=True,
        development_restore_fence=True,public_ephemeris='/public.bsp',owner_id=101,connections=roles,
        catalog=dict(synthetic=True,astronomy_enabled=False,fixtures={}),command_key=key,tick_key=secrets.token_hex(32),
        review_key=secrets.token_hex(32))))
    write('worker.json',json.dumps(roles['worker']))
    write('gateway.json',json.dumps({'key':key}))
    write('compose.json',json.dumps(definition(images)))
    write('pin',json.dumps([a.daemon,a.revision]))

def sql(*args, **kw):
    return compose('exec','-T','db','sh','-ec','export PGPASSWORD="$(cat /run/pass)"; exec "$@"','sh',*args,**kw)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','initialize','start','status','stop','fence','backup'])
    for key in ('daemon','revision','app','db','relay','kernel','recipient','certificate','destination','destination_daemon','ticket','authority','authority_sha','signature'):
        parser.add_argument('--'+key, required=key in ('daemon','revision'))
    a = parser.parse_args()
    os.umask(0o077)
    if any(k.startswith(('DOCKER_','COMPOSE_')) for k in os.environ):
        raise ValueError('ambient override')
    if docker('info','--format','{{.ID}}',capture_output=True,text=True,timeout=10).stdout.strip()!=a.daemon:
        raise ValueError('daemon mismatch')
    if cmd(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip()!=a.revision or cmd(['git','status','--porcelain'],cwd=ROOT,capture_output=True).stdout.strip():
        raise ValueError('checkout mismatch')
    if a.action=='prepare':
        if a.ticket or 'microsoft' not in Path('/proc/sys/kernel/osrelease').read_text().lower():
            validate_transfer(a)
        return prepare(a)
    import fcntl
    lock=(STATE/'control.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX)
    if json.loads((STATE/'pin').read_text()) != [a.daemon,a.revision]:
        raise ValueError('state mismatch')
    if a.action in ('start','initialize') and (STATE/'FENCED').exists():
        raise ValueError('host fenced')
    if a.action=='initialize':
        compose('up','-d','--pull','never','--wait','--wait-timeout','60','db')
        with (STATE/'init.sql').open('rb') as source:
            sql('psql','-Xq','-v','ON_ERROR_STOP=1','-U','synthetic_test','-d',DB,stdin=source,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        compose('up','-d','--pull','never','relay','app')
        compose('run','--rm','--no-deps','--entrypoint','python','gateway','/src/staging/laptop/service.py','install',timeout=180)
        write('initialized','true')
    elif a.action=='start':
        if not (STATE/'initialized').exists():
            raise ValueError('initialize first')
        compose('up','-d','--pull','never','--wait','--wait-timeout','120')
    elif a.action in ('fence','stop'):
        if a.action=='fence':
            (STATE/'FENCED').touch()
        compose('stop','-t','40','gateway','worker','app')
        compose('stop','-t','40','relay','db')
        if a.action=='fence':
            if not a.destination_daemon or a.destination_daemon==a.daemon or compose('ps','--status','running','-q',capture_output=True).stdout.strip():
                raise ValueError('Stopped source and distinct destination required')
            print(json.dumps(dict(source=a.daemon,destination=a.destination_daemon,revision=a.revision,
                                  project=PROJECT,fenced_at=int(time.time())),sort_keys=True))
    elif a.action=='status':
        result=json.loads(compose('exec','-T','gateway','python','/src/staging/laptop/service.py','probe',capture_output=True,text=True,timeout=12).stdout)
        for role in ('app','gateway'):
            compose('exec','-T',role,'python','/src/staging/laptop/service.py','health',timeout=8)
        compose('exec','-T','worker','python','/src/staging/laptop/service.py','health',timeout=8)
        if not all(type(result.get(k)) is int and result[k]>=0 for k in ('due','uncertain','dead','sending')):
            raise ValueError('Malformed health response')
        print(json.dumps(result))
    else:
        backup(a)

def encrypt_command(fingerprint,certificate,path):
    der=cmd(['openssl','x509','-in',str(certificate),'-outform','DER'],capture_output=True).stdout
    if hashlib.sha256(der).hexdigest()!=fingerprint:
        raise ValueError('Backup recipient mismatch')
    return ['openssl','cms','-encrypt','-binary','-stream','-outform','DER','-aes-256-gcm',
            '-out',str(path),str(certificate)]

def backup(a):
    import tempfile
    import re
    dest=Path(a.destination).resolve(strict=True)
    if not dest.is_dir() or not re.fullmatch(r'[a-f0-9]{64}',a.recipient):
        raise ValueError('mounted destination and certificate SHA-256 required')
    fs=cmd(['findmnt','-T',str(dest),'-n','-o','FSTYPE'],capture_output=True,text=True).stdout.strip()
    if fs not in ('nfs','nfs4','cifs','fuse.sshfs'):
        raise ValueError('off-host filesystem required')
    with tempfile.TemporaryDirectory(dir=dest) as tmp:
        path=Path(tmp)/'encrypted'
        with subprocess.Popen(encrypt_command(a.recipient,a.certificate,path),stdin=subprocess.PIPE) as enc:
            try:
                sql('pg_dump','-Fc','-U','synthetic_test','-d',DB,stdout=enc.stdin)
            finally:
                enc.stdin.close()
            if enc.wait()!=0:
                raise ValueError('encryption failed')
        with path.open('rb') as stream:
            digest=hashlib.file_digest(stream,'sha256').hexdigest()
        os.link(path,dest/(digest+'.dump.cms'))
        print(json.dumps({'backup_sha256':digest}))

if __name__=='__main__':
    try:
        main()
    except Exception:
        sys.exit('Staging action failed; inspect the approved local inputs.')
