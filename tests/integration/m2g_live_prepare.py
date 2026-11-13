"""Gated future private-bot acceptance. No live action without BOTH approval flags."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from m2g_runner import M2GRunner
import runner as base
from dincharya.lunar_runtime import read_private,validate_test_bot


class LiveRunner(M2GRunner):
    server_script='m2g_live_server.py'
    due_seconds=1200
    telegram=None
    def configure_service(self):
        self.config['catalog']['fixtures']={'success':self.config['catalog']['fixtures']['success']}
        self.config['telegram']=self.telegram;self.config['delivery_enabled']=True
        self.config['live_gateway_approved']=True
    def tests(self):
        with tempfile.TemporaryDirectory(prefix='m2g-live-') as directory:
            self.directory=Path(directory);self.service=None;self.bridge=None;self.relays=[]
            try:
                self.setup()
                gateway_config={k:self.config[k] for k in ('owner_id','telegram','delivery_enabled','live_gateway_approved','command_key','tick_key')}
                gateway_config['n8n_socket']=self.n8n_socket
                path=self.directory/'acceptance.json'
                fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(fd,'w') as file:json.dump(gateway_config,file)
                print('Private acceptance configuration: '+str(path),flush=True)
                print('Start gateway in a second terminal using the documented explicit live-approved command. Stop gateway before typing STOP here.',flush=True)
                base.require(input().strip()=='STOP','Live acceptance stopped without completion confirmation')
                summary=self.app_sql("SELECT coalesce(jsonb_agg(jsonb_build_object('state',status,'attempts',attempts,'has_receipt',telegram_message_id IS NOT NULL)),'[]') FROM public.reminder_deliveries")
                print('Sanitized delivery summary: '+summary,flush=True)
                rows=self.app_sql("SELECT count(*),count(*) FILTER(WHERE status='sent' AND attempts=1 AND telegram_chat_id IS NOT NULL AND telegram_message_id IS NOT NULL) FROM public.reminder_deliveries")
                base.require(rows=='1|1','Live result incomplete/uncertain or not exactly one; no automatic resend')
                base.require(self.app_sql('SELECT count(*) FROM lunar_private.series')=='1','More than one live request submitted')
                print('PASS one acknowledged live reminder; owner must separately confirm exactly one received message',flush=True)
            finally:
                self.stop_service()
                if self.bridge:
                    self.bridge.stdin.close()
                    try:self.bridge.wait(timeout=10)
                    except Exception:self.bridge.kill();self.bridge.wait(timeout=5)
                for relay in self.relays:relay.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--credentials',type=Path,required=True)
    parser.add_argument('--baseline',type=Path,required=True);parser.add_argument('--expected-daemon-id',required=True)
    parser.add_argument('--execute-approved',action='store_true');parser.add_argument('--live-approved',action='store_true');args=parser.parse_args()
    try:
        base.require(args.execute_approved and args.live_approved,'Separate explicit live test approval required')
        info=read_private(args.credentials)
        validate_test_bot(info,info.get('owner_id'))
        base.require(args.baseline.is_file() and not args.baseline.is_symlink(),'Named regular schema required')
        LiveRunner.telegram=info;LiveRunner.owner_id=info['owner_id'];LiveRunner.baseline=args.baseline
        base.Runner=LiveRunner;base.execute(args.expected_daemon_id)
    except Exception as error:
        print(str(error) if isinstance(error,base.Failure) else 'Live acceptance stopped; private details suppressed',file=sys.stderr);return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
