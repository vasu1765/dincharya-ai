import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

from dincharya.beta_archive import seal


class SyntheticBackupTests(unittest.TestCase):
    def test_pinned_encryption_and_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cert, key = root / "cert", root / "key"
            subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                            "-subj", "/CN=synthetic", "-days", "1", "-keyout", str(key),
                            "-out", str(cert)], capture_output=True, check=True)
            data = b"synthetic archive fixture"
            with tempfile.TemporaryFile() as source:
                source.write(data)
                source.seek(0)
                with self.assertRaises(ValueError):
                    seal(source, root, cert, "0" * 64)
                self.assertFalse(list(root.glob("*.cms")))
                digest = seal(source, root, cert, hashlib.sha256(cert.read_bytes()).hexdigest())
            archive = root / (digest + ".cms")
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), digest)
            command = ["openssl", "cms", "-decrypt", "-binary", "-inform", "DER",
                       "-inkey", str(key), "-in", str(archive)]
            self.assertEqual(subprocess.check_output(command), data)
            altered = bytearray(archive.read_bytes())
            altered[-1] ^= 1
            archive.write_bytes(altered)
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
