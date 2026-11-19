"""Verify an independently received Stage 2 manifest on the approved recovery host."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from complete import history,require
from control import ROOT
from restore import restore

def main():
    require(not any(k.startswith(('DOCKER_','COMPOSE_')) for k in os.environ),'ambient override')
    raw=Path(os.environ['MANIFEST']).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==os.environ['MANIFEST_SHA256'],'manifest integrity')
    m=json.loads(raw)
    require(m['revision']==os.environ['REV']==subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
            and not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT),'recovery checkout')
    require(os.environ['RECOVERY_DAEMON']!='44c1ef83-c50e-4ecc-8f19-4b112bc40f29','independent daemon required')
    restore(Path(os.environ['OFFHOST'])/(m['digest']+'.dump.cms'),os.environ['TEST_KEY'],m['digest'],
            os.environ['PG'],os.environ['RECOVERY_DAEMON'],
            verify=lambda read:require(history(read)==m['history'],'restored history mismatch'))
    print('PASS off-device recovery, migration checksums and six table histories')

if __name__=='__main__':
    main()
