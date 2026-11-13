"""Real application service process; ONLY outbound Telegram HTTP is simulated."""
from pathlib import Path
import json
import sys
import threading
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from dincharya.lunar_runtime import build_service
from dincharya.lunar_service import connection_factory
from dincharya.lunar_http import server
from dincharya.reminder_adapters import TelegramReminders


class SimulatedTelegramWire:
    def __init__(self,settings):
        self.connect=connection_factory(settings);self.local=threading.local()
        self.adapter=TelegramReminders(self.post,'123456:offline',101)
    def send(self,payload):self.local.payload=payload;return self.adapter.send(payload)
    def post(self,url,*,json):
        payload=self.local.payload;mode=payload['title'].rsplit(': ',1)[-1]
        if mode=='anniversary':mode='success'
        with self.connect() as conn:
            mid=conn.execute('SELECT message_id FROM synthetic_e2e.record_attempt(%s,%s)',(payload['event_id'],mode)).fetchone()[0]
        body={'ok':True,'result':{'chat':{'id':101},'message_id':mid}}
        status=200
        if mode=='failure':status=400;body={'ok':False,'error_code':400}
        if mode=='uncertain':status=500;body={'ok':False}
        class Response:
            status_code=status
            def json(self):return body
        return Response()


def main():
    config=json.loads(sys.stdin.readline())
    service=build_service(config,transport=SimulatedTelegramWire(config['transport_connection']))
    path=config['service_socket']
    with server(path,service) as instance:
        thread=threading.Thread(target=instance.serve_forever,daemon=True);thread.start()
        print('{"ready":true}',flush=True)
        try:
            if sys.stdin.readline().strip()!='stop':raise ValueError()
        finally:instance.shutdown();thread.join(timeout=5)
    Path(path).unlink(missing_ok=True)

if __name__=='__main__':
    try:main()
    except Exception:
        print('M2G service failure; private details suppressed',file=sys.stderr);raise SystemExit(1)
