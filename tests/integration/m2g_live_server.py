"""Future explicitly approved live-test lifecycle host. Never used in simulation."""
from pathlib import Path
import json
import sys
import threading
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from dincharya.lunar_runtime import build_service
from dincharya.lunar_http import server


def main():
    config=json.loads(sys.stdin.readline())
    if config.get('live_gateway_approved') is not True:raise ValueError('Explicit live authorization required')
    service=build_service(config,live_approved=True)
    with server(config['service_socket'],service) as instance:
        thread=threading.Thread(target=instance.serve_forever,daemon=True);thread.start()
        print('{"ready":true}',flush=True)
        try:
            if sys.stdin.readline().strip()!='stop':raise ValueError('Invalid lifecycle command')
        finally:instance.shutdown();thread.join(timeout=5)
    Path(config['service_socket']).unlink(missing_ok=True)

if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('Live acceptance service failed; private details suppressed') from None
