import hashlib
import json
import ssl
import unittest
from unittest.mock import Mock, patch

from dincharya.attended_operator import Approval, Telegram, telegram_transport
from dincharya.attended_connect import PROXY
from scripts.attended_operator_host import laptop_topology


class LaptopProfileTests(unittest.TestCase):
    def setUp(self):
        self.data=dict(sha="a"*40,host="acer",pg="sha256:"+"b"*64,app="sha256:"+"c"*64,n8n="sha256:"+"d"*64,
                       bot=9202,owner=9201,start=1795564800,end=1795568400,
                       silent="Schedule Quiet on 2026-11-25 at 05:40",reminder="Schedule Study on 2026-11-25 at 05:50",
                       question="What was the tithi on 2023-12-06?",kernel_sha256="f"*64,bot_username="DedicatedTestBot")

    def manifest(self,**fields):
        data=json.dumps(dict(self.data,**fields)).encode()
        return Approval.load(data,hashlib.sha256(data).hexdigest(),self.data["sha"],"acer")

    def test_direct_requires_explicit_signed_profile(self):
        a=self.manifest(profile="laptop-beta")
        self.assertIsNone(a.telegram_ipv4)
        for change in ({},{"profile":"desktop"},{"profile":"laptop-beta","telegram_ipv4":"93.184.216.34"}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.manifest(**change)
        self.assertEqual(self.manifest(telegram_ipv4="93.184.216.34").profile,"hardened")

    def test_transport_is_explicit_and_never_falls_back(self):
        ctx=ssl.create_default_context()
        for profile,proxy in (("laptop-beta",None),("hardened",PROXY)):
            with patch("httpx.HTTPTransport",side_effect=RuntimeError) as make,self.assertRaises(RuntimeError):
                telegram_transport(ctx,profile)
            make.assert_called_once_with(proxy=proxy,verify=ctx,retries=0,trust_env=False)
        with self.assertRaises(ValueError):
            telegram_transport(ctx,"unrecognized")

    def test_identity_still_required(self):
        a=self.manifest(profile="laptop-beta")
        c=Mock()
        tg=Telegram(c,"9202:"+"s"*32,a)
        for uid,name in ((9202,"WrongBot"),(9203,a.bot_username)):
            c.post.return_value.json.return_value={"ok":True,"result":{"id":uid,"username":name,"is_bot":True}}
            with self.assertRaises(ValueError):
                tg.me()
        with self.assertRaises(ValueError):
            tg.send(chat_id=2,text="denied")

    def test_laptop_topology_fails_closed(self):
        def container(name,extra=False):
            nets={"service":{"Aliases":[name]}}
            if extra:
                nets["out"]={"Aliases":[]}
            return dict(Id=name,NetworkSettings={"Networks":nets},Mounts=[],HostConfig={"Tmpfs":{"/home/node/.n8n":""},"ExtraHosts":[],"PublishAllPorts":False})
        pg,app,relay=container("db"),container("app",True),container("relay")
        peers={"service":["db","app","relay"],"out":["app"]}
        def inspect(*args):
            name=args[-1]
            return json.dumps([dict(Driver="bridge",Internal=name=="service",EnableIPv6=False,Containers=dict.fromkeys(peers[name]))])
        with patch("scripts.attended_operator_host.output",side_effect=inspect):
            laptop_topology(pg,app,relay)
            peers["out"].append("foreign")
            with self.assertRaises(ValueError):
                laptop_topology(pg,app,relay)
            peers["out"].pop()
            pg["HostConfig"]["PublishAllPorts"]=True
            with self.assertRaises(ValueError):
                laptop_topology(pg,app,relay)

    def test_cli_rejects_profile_mismatch_before_secrets(self):
        import sys
        from dincharya.attended_operator import main
        data=json.dumps(dict(self.data,profile="laptop-beta")).encode()
        pin=hashlib.sha256(data).hexdigest()
        with patch.object(sys,"argv",["operator","--attended","--approval",pin]),patch(
                "pathlib.Path.read_bytes",return_value=data),patch("pathlib.Path.read_text",return_value=self.data["sha"]),patch(
                "socket.gethostname",return_value="acer"),self.assertRaisesRegex(ValueError,"profiles? differ"):
            main()

    def test_direct_tls_ignores_ambient_proxy(self):
        import httpx
        import os
        import subprocess
        import tempfile
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from pathlib import Path
        class Fixture(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(204)
                self.end_headers()
            def log_message(self,*args):
                pass
        with tempfile.TemporaryDirectory() as tmp:
            cert,key=Path(tmp)/"cert",Path(tmp)/"key"
            subprocess.run(["openssl","req","-x509","-nodes","-newkey","rsa:2048","-days","1","-subj",
                            "/CN=localhost","-addext","subjectAltName=DNS:localhost","-out",str(cert),
                            "-keyout",str(key)],capture_output=True,check=True)
            with HTTPServer(("127.0.0.1",0),Fixture) as server:
                tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                tls.load_cert_chain(cert,key)
                server.socket=tls.wrap_socket(server.socket,server_side=True)
                t=threading.Thread(target=server.serve_forever,daemon=True)
                t.start()
                try:
                    ctx=ssl.create_default_context(cafile=cert)
                    with patch.dict(os.environ,{"HTTPS_PROXY":"http://127.0.0.1:1","NO_PROXY":""}),httpx.Client(
                            transport=telegram_transport(ctx,"laptop-beta"),trust_env=False,timeout=2) as client:
                        self.assertEqual(client.get(f"https://localhost:{server.server_port}").status_code,204)
                        with self.assertRaises(httpx.ConnectError):
                            client.get(f"https://127.0.0.1:{server.server_port}")
                finally:
                    server.shutdown()
                    t.join()
