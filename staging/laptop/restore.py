"""Verify a staging ciphertext in an ephemeral, networkless PG17 container."""
import hashlib
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
from time import sleep

from control import DB, docker

def restore(archive, private_key, digest, image, daemon, *, verify=None):
    if docker('info','--format','{{.ID}}',capture_output=True,text=True).stdout.strip()!=daemon:
        raise ValueError('unexpected daemon')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}',image):
        raise ValueError('pin local image')
    with Path(archive).open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=digest:
            raise ValueError('integrity mismatch')
    name='dincharya-laptop-restore-'+secrets.token_hex(8)
    # Disposable memory-backed storage. No application connection or host port.
    cid=docker('run','--pull','never','-d','--network','none','--name',name,
        '--tmpfs','/var/lib/postgresql/data:rw','-e','POSTGRES_HOST_AUTH_METHOD=trust',
        '-e','POSTGRES_USER=synthetic_test','-e','POSTGRES_DB='+DB,image,'postgres','-c','listen_addresses=',
        capture_output=True,text=True).stdout.strip()
    try:
        pg=['exec','-i',cid,'psql','-XAtq','-U','synthetic_test','-d',DB,'-v','ON_ERROR_STOP=1']
        for _ in range(60):
            try:
                if docker(*pg,'-c','SHOW server_version_num',capture_output=True,text=True).stdout.startswith('17') and docker('exec',cid,'cat','/proc/1/comm',capture_output=True,text=True).stdout.strip()=='postgres':
                    break
            except subprocess.CalledProcessError:
                pass
            sleep(1)
        else:
            raise ValueError('restore readiness timeout')
        from control import ROOT
        roles=set()
        for p in (ROOT/'database/migrations').glob('*.sql'):
            roles.update(re.findall(r'\bdincharya_[a-z_]+\b',p.read_text()))
        for role in sorted(roles-{'dincharya_app_test'}):
            docker(*pg,'-c','CREATE ROLE '+role+' NOLOGIN',capture_output=True)
        with subprocess.Popen(['openssl','cms','-decrypt','-binary','-inform','DER','-inkey',private_key,'-in',archive],stdout=subprocess.PIPE) as dec:
            docker('exec','-i',cid,'pg_restore','--single-transaction','--no-owner','--no-acl','-U',
                'synthetic_test','-d',DB,stdin=dec.stdout,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            if dec.wait()!=0:
                raise ValueError('decryption failed')
        rows=docker(*pg,'-c','SELECT version,checksum FROM public.application_migration_ledger ORDER BY version',
                    capture_output=True,text=True).stdout.splitlines()
        expected=[p.name+'|'+hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'database/migrations').glob('*.sql'))]
        if rows!=expected:
            raise ValueError('restore ledger mismatch')
        docker(*pg,'-c','SELECT lunar_private.fence_restored_pending()',capture_output=True)
        if verify:
            verify(lambda statement: docker(*pg,'-c',statement,capture_output=True,text=True).stdout.strip())
        print(docker(*pg,'-c',"SELECT json_build_object('slots',count(*),'sent',count(*) FILTER(WHERE status='sent'), 'uncertain',count(*) FILTER(WHERE status='uncertain')) FROM lunar_private.notification_slot",capture_output=True,text=True).stdout.strip())
    finally:
        docker('rm','-fv',cid,stdout=subprocess.DEVNULL)

if __name__=='__main__':
    try:
        restore(*sys.argv[1:])
    except Exception:
        sys.exit('Isolated restore verification failed')
