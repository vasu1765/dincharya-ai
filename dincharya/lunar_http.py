"""Authenticated bounded HTTP endpoint; Unix socket supports local acceptance."""
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn,UnixStreamServer
import json
import os


def server(path,service):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            result={'status':'denied'}
            try:
                length=int(self.headers.get('Content-Length','0'))
                if self.path!='/lunar' or not 0<length<=16384 or self.headers.get('Transfer-Encoding'):raise ValueError()
                value=json.loads(self.rfile.read(length))
                result=service.handle(value,self.headers.get('x-dincharya-signature',''))
            except Exception:pass
            raw=json.dumps(result,separators=(',',':')).encode()
            self.send_response(403 if result['status']=='denied' else 200)
            self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)))
            self.end_headers();self.wfile.write(raw)
    class Server(ThreadingMixIn,UnixStreamServer):daemon_threads=True
    instance=Server(path,Handler);os.chmod(path,0o600);return instance
