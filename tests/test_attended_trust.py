"""Loopback-only TLS and dependency boundary tests, with fresh synthetic keys."""
import socket
import ssl
import subprocess
import tempfile
import threading
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from dincharya.attended_runtime import PG, APP, N8N, WHEEL, isolated_lookup, telegram_tls, verify_images


def exercise_tls(runtime_context):
    if not runtime_context.check_hostname or runtime_context.verify_mode != ssl.CERT_REQUIRED:
        raise AssertionError("TLS identity verification required")
    with tempfile.TemporaryDirectory() as directory:
        cert = Path(directory)/"fixture.pem"
        key = Path(directory)/"fixture.key"
        subprocess.run(["openssl","req","-x509","-newkey","rsa:2048","-nodes","-days","1",
                        "-subj","/CN=localhost","-addext","subjectAltName=DNS:localhost",
                        "-keyout",str(key),"-out",str(cert)],check=True,capture_output=True)
        server=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server.load_cert_chain(cert,key)
        fixture=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        fixture.load_verify_locations(cafile=str(cert))
        with socket.socket() as listener:
            listener.bind(("127.0.0.1",0))
            listener.listen()
            listener.settimeout(3)
            def serve():
                for _ in range(3):
                    stream,_=listener.accept()
                    with stream:
                        try:
                            with server.wrap_socket(stream,server_side=True) as tls:
                                tls.sendall(b"ok")
                        except ssl.SSLError:
                            pass
            thread=threading.Thread(target=serve,daemon=True)
            thread.start()
            for ctx,name,expected in [(runtime_context,"localhost",False),(fixture,"wrong.invalid",False),
                                      (fixture,"localhost",True)]:
                with socket.create_connection(listener.getsockname(),timeout=2) as stream:
                    try:
                        with ctx.wrap_socket(stream,server_hostname=name) as tls:
                            accepted=tls.recv(8)==b"ok"
                    except ssl.SSLCertVerificationError:
                        accepted=False
                    if accepted!=expected:
                        raise AssertionError("Unexpected fixture TLS result")
            thread.join(4)
            if thread.is_alive():
                raise AssertionError("TLS fixture did not terminate")


class RuntimeTests(TestCase):
    def test_tls_handshakes(self):
        exercise_tls(ssl.create_default_context())

    def test_image_substitution(self):
        verify_images(PG,APP,N8N)
        with self.assertRaises(ValueError):
            verify_images(PG,N8N,APP)

    def test_legacy_certifi_refused_by_parent(self):
        with patch("dincharya.attended_runtime.metadata.distribution",return_value=Mock(version="2025.10.5")),self.assertRaises(ValueError):
            telegram_tls()

    def test_bad_wheel_never_starts_child(self):
        with tempfile.TemporaryDirectory() as d:
            wheel=Path(d)/WHEEL
            wheel.write_bytes(b"changed")
            with patch("subprocess.run") as run,self.assertRaises(ValueError):
                isolated_lookup("question",Path("/kernel"),wheel)
            run.assert_not_called()

    def test_worker_inherits_no_parent_environment(self):
        with tempfile.TemporaryDirectory() as d:
            wheel=Path(d)/WHEEL
            wheel.write_bytes(b"fixture")
            import hashlib
            with patch("dincharya.attended_runtime.WHEEL_SHA",hashlib.sha256(b"fixture").hexdigest()),patch(
                    "subprocess.run",return_value=Mock(returncode=0,stdout="reply")) as run:
                self.assertEqual(isolated_lookup("question",Path("/kernel"),wheel),"reply")
            args,kw=run.call_args
            self.assertEqual(args[0][1:4],["-I","-S","-B"])
            self.assertEqual(kw["env"],{"TZ":"UTC"})
            self.assertTrue(kw["close_fds"])

    def test_changed_ca_bytes_refused(self):
        from types import SimpleNamespace
        class Entry:
            hash=SimpleNamespace(mode="sha256",value="incorrect")
            def __str__(self):
                return "certifi/cacert.pem"
            def locate(self):
                return Path(__file__)
        dist=SimpleNamespace(version="2026.10.23",files=[Entry()])
        with patch("dincharya.attended_runtime.metadata.distribution",return_value=dist),self.assertRaises(ValueError):
            telegram_tls()
