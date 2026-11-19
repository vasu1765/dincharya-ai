"""Attended independent observer. SSH alias must use an approved forced status command."""
import argparse
import datetime
import json
import re
import subprocess
import time


def observe(alias, samples, interval=15, revision=None):
    if not re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9-]{0,60}',alias):
        raise ValueError('Expected a pinned SSH config alias')
    misses=0
    for n in range(samples):
        start=time.monotonic()
        try:
            reply=subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
                '-o','ConnectTimeout=4',alias,'status'],capture_output=True,text=True,check=True,timeout=10)
            v=json.loads(reply.stdout)
            if v['relay']!='ready' or not all(type(v[k]) is int and v[k]>=0 for k in ('due','uncertain','dead','sending')):
                raise ValueError('Invalid status')
            if revision and (v.get("revision")!=revision or v.get("project")!="dincharya-stage2-physical"):
                raise ValueError("Unexpected monitor target")
            misses=0
            state='attention' if v['uncertain'] or v['dead'] else 'ready'
        except (ValueError,KeyError,subprocess.SubprocessError,OSError):
            misses+=1
            state='outage' if misses>=2 else 'miss'
            v={}
        print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),state=state,
                              **({"revision":revision} if revision else {}),
                              **{k:v[k] for k in ('due','uncertain','dead','sending') if k in v})),flush=True)
        if state in ('attention','outage'):
            print('\aOwner attention required',file=__import__('sys').stderr,flush=True)
        if n+1<samples:
            time.sleep(max(0,interval-time.monotonic()+start))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('alias')
    parser.add_argument('--samples',type=int,default=240)
    parser.add_argument('--stage2-revision')
    args=parser.parse_args()
    if args.stage2_revision and not re.fullmatch('[0-9a-f]{40}',args.stage2_revision):
        parser.error('Invalid revision')
    if not 1<=args.samples<=480:
        parser.error('Use 1–480 samples')
    observe(args.alias,args.samples,revision=args.stage2_revision)
