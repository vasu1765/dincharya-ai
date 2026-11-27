"""Exercise the backup transfer boundary using real CMS and a fake Drive client."""
import hashlib
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from dincharya.beta_archive import seal

UPLOAD = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/daily-drive-upload.py"))["upload"]


@unittest.skipUnless(shutil.which("openssl"), "OpenSSL required for synthetic CMS")
class DailyDriveUploadTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        certificate = self.root / "recipient.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                        "-subj", "/CN=Synthetic", "-out", str(certificate), "-keyout", str(self.root / "test.key")],
                       check=True, capture_output=True)
        data = self.root / "invented"
        data.write_bytes(b"synthetic backup fixture")
        self.folder = "SyntheticFolder123"
        self.config = self.root / "drive.conf"
        self.config.write_text("[dincharya-drive]\ntype=drive\nscope=drive.file\n"
                               "root_folder_id=SyntheticFolder123\ntoken=invented\n")
        self.config.chmod(0o600)
        with data.open("rb") as source:
            self.digest = seal(source, self.root, certificate, hashlib.sha256(certificate.read_bytes()).hexdigest())
        self.archive = self.root / (self.digest + ".cms")
        self.rclone = self.root / "rclone"
        self.rclone.write_text("""#!/usr/bin/env python3
import os
from pathlib import Path
import shutil
import sys

args = sys.argv[1:]
remote = Path(__file__).with_name("remote")
assert not any(k.startswith("RCLONE_") for k in os.environ)
assert "dincharya-drive:" in " ".join(args)
if "copyto" in args:
    assert "--immutable" in args
    shutil.copyfile(args[-2], remote)
elif "cat" in args:
    assert "--count" in args
    sys.stdout.buffer.write(remote.read_bytes() + (b"z" if os.getenv("SYNTHETIC_CORRUPTION") else b""))
else:
    raise AssertionError("unexpected Drive operation")
""")
        self.rclone.chmod(0o700)

    def test_upload_and_bounded_readback(self):
        with patch.dict(os.environ, {"RCLONE_DRIVE_SCOPE": "drive"}):
            self.assertEqual(UPLOAD(self.archive, self.config, self.folder, self.rclone), self.digest)

    def test_refuses_different_destination_or_scope_before_transfer(self):
        with self.assertRaises(ValueError):
            UPLOAD(self.archive, self.config, "OtherFolder123", self.rclone)
        self.config.write_text(self.config.read_text().replace("scope=drive.file", "scope=drive"))
        with self.assertRaises(ValueError):
            UPLOAD(self.archive, self.config, self.folder, self.rclone)
        self.assertFalse((self.root / "remote").exists())

    def test_refuses_plaintext_and_symlinks_before_transfer(self):
        path = self.root / (hashlib.sha256(b"plain").hexdigest() + ".cms")
        path.write_bytes(b"plain")
        path.chmod(0o600)
        with self.assertRaises(ValueError):
            UPLOAD(path, self.config, self.folder, self.rclone)
        path.unlink()
        path.symlink_to(self.archive)
        with self.assertRaises(OSError):
            UPLOAD(path, self.config, self.folder, self.rclone)
        self.assertFalse((self.root / "remote").exists())

    def test_remote_corruption_is_a_failure(self):
        with patch.dict(os.environ, {"SYNTHETIC_CORRUPTION": "1"}), self.assertRaises(ValueError):
            UPLOAD(self.archive, self.config, self.folder, self.rclone)
