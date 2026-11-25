import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from dincharya.attended_connect import AUTHORITY, permitted, upstream
from dincharya.attended_operator import Telegram
from scripts.attended_net_policy import rules, verify


class BoundaryTests(unittest.TestCase):
    def test_exact_authority(self):
        head=b"CONNECT "+AUTHORITY+b" HTTP/1.1\r\nHost: "+AUTHORITY+b"\r\nAccept: */*\r\n\r\n"
        self.assertTrue(permitted(head))
        for other in (b"api.telegram.org:80",b"api.telegram.org.:443",b"1.1.1.1:443",
                      b"[::1]:443",b"evil.invalid:443",b"api.telegram.org@host:443"):
            self.assertFalse(permitted(head.replace(AUTHORITY,other)))
        for line in (b"Host: api.telegram.org:443",b"Transfer-Encoding: chunked",b"Proxy-Authorization: x"):
            self.assertFalse(permitted(head[:-2]+line+b"\r\n\r\n"))
        self.assertFalse(permitted(head.replace(b"CONNECT ",b"GET ")))

    def test_address_pins(self):
        for pin in ("localhost","127.0.0.1","::1","224.0.0.1","192.168.2.1","0.0.0.0"):
            with self.assertRaises(ValueError):
                upstream(pin)

    def test_exact_rules_required(self):
        pin="93.184.216.34"
        for role in ("app","gateway","db","relay"):
            expected=rules(role,pin)
            self.assertIn("policy drop;",expected)
            self.assertNotIn("udp",expected)
            with patch("os.stat",side_effect=[SimpleNamespace(st_ino=1),SimpleNamespace(st_ino=2)]), patch("subprocess.check_output",return_value=expected):
                verify(88,role,pin)
            with patch("os.stat",side_effect=[SimpleNamespace(st_ino=1),SimpleNamespace(st_ino=2)]), patch("subprocess.check_output",return_value=expected.replace("policy drop","policy accept")),self.assertRaises(ValueError):
                verify(88,role,pin)

    def test_both_identity_fields(self):
        from types import SimpleNamespace
        a=SimpleNamespace(bot=902,owner=901,bot_username="OwnerChosenBot")
        c=Mock()
        tg=Telegram(c,"902:"+"s"*32,a)
        for uid,name,accepted in ((902,a.bot_username,True),(903,a.bot_username,False),(902,"ownerchosenbot",False)):
            c.post.return_value.json.return_value={"ok":True,"result":{"id":uid,"username":name,"is_bot":True}}
            if accepted:
                self.assertEqual(tg.me()["username"],name)
            else:
                with self.assertRaises(ValueError):
                    tg.me()

    def test_explicit_proxy_keeps_tls_context(self):
        import ssl
        from dincharya.attended_operator import telegram_transport
        from dincharya.attended_connect import PROXY
        ctx=ssl.create_default_context()
        with patch("httpx.HTTPTransport") as factory:
            telegram_transport(ctx)
        factory.assert_called_once_with(proxy=PROXY,verify=ctx,retries=0,trust_env=False)

    def test_service_peer_rejected_before_read_or_connect(self):
        import asyncio
        from unittest.mock import AsyncMock
        from dincharya.attended_connect import tunnel
        client=Mock()
        client.get_extra_info.return_value=("172.29.240.3",4000)
        reader=AsyncMock()
        with patch("asyncio.open_connection",new_callable=AsyncMock) as dial:
            asyncio.run(tunnel(reader,client,"93.184.216.34"))
        dial.assert_not_awaited()
        reader.readuntil.assert_not_awaited()
        client.close.assert_called_once()

    def test_httpx_connect_carries_end_to_end_tls(self):
        import asyncio
        import httpx
        import ssl
        import subprocess
        import tempfile
        from pathlib import Path
        from dincharya import attended_connect as gateway
        async def exercise(cert,key):
            tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            tls.load_cert_chain(cert,key)
            async def origin(reader,writer):
                await reader.readuntil(b"\r\n\r\n")
                writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
                await writer.drain()
                writer.close()
            origin_server=await asyncio.start_server(origin,"127.0.0.1",0,ssl=tls)
            port=origin_server.sockets[0].getsockname()[1]
            original=asyncio.open_connection
            def dial(host,dest_port):
                self.assertEqual((host,dest_port),("93.184.216.34",443))
                return original("127.0.0.1",port)
            async with origin_server:
                proxy=await asyncio.start_server(lambda r,w:gateway.tunnel(r,w,"93.184.216.34"),"127.0.0.1",0)
                async with proxy:
                    proxy_url="http://127.0.0.1:"+str(proxy.sockets[0].getsockname()[1])
                    def request():
                        transport=httpx.HTTPTransport(verify=ssl.create_default_context(cafile=cert),
                                                       retries=0,proxy=proxy_url,trust_env=False)
                        with httpx.Client(transport=transport,trust_env=False,timeout=2) as client:
                            return client.get("https://api.telegram.org/fixture").text
                    with patch.object(gateway,"OPERATOR","127.0.0.1"),patch.object(asyncio,"open_connection",new=dial):
                        self.assertEqual(await asyncio.to_thread(request),"ok")
        with tempfile.TemporaryDirectory() as tmp:
            cert,key=Path(tmp)/"cert",Path(tmp)/"key"
            subprocess.run(["openssl","req","-x509","-nodes","-newkey","rsa:2048","-days","1","-subj",
                            "/CN=api.telegram.org","-addext","subjectAltName=DNS:api.telegram.org",
                            "-out",str(cert),"-keyout",str(key)],capture_output=True,check=True)
            asyncio.run(exercise(cert,key))

    def test_service_peer_or_direct_uplink_fails_preflight(self):
        import json
        from scripts.attended_operator_host import topology
        def c(name,**nets):
            return {"Id":name,"NetworkSettings":{"Networks":{k:{"IPAddress":v} for k,v in nets.items()}}}
        pg=c("pg",service="172.29.240.3")
        app=c("app",service="172.29.240.2",link="172.29.241.2")
        relay=c("relay",service="172.29.240.4")
        gw=c("gw",link="172.29.241.3",uplink="172.29.242.2")
        peers={"service":["pg","app","relay"],"link":["app","gw"],"uplink":["gw"]}
        def inspect(*args):
            name=args[-1]
            return json.dumps([dict(Driver="bridge",Internal=name!="uplink",EnableIPv6=False,
                                    Containers=dict.fromkeys(peers[name]))])
        with patch("scripts.attended_operator_host.output",side_effect=inspect):
            topology(pg,app,relay,gw)
            peers["link"].append("relay")
            with self.assertRaises(ValueError):
                topology(pg,app,relay,gw)
            peers["link"].pop()
            app["NetworkSettings"]["Networks"]["uplink"]={"IPAddress":"172.29.242.3"}
            with self.assertRaises(ValueError):
                topology(pg,app,relay,gw)
