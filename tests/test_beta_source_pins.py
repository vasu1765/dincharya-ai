"""Offline tests: reviewed beta source pins are immutable and non-executable."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check-beta-source-pins.py"
spec = importlib.util.spec_from_file_location("beta_source_verifier", SCRIPT)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class BetaSourcePinsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "safe").mkdir()
        self.source = self.root / "safe" / "candidate.txt"
        self.source.write_bytes(b"fixture-only")
        self.manifest = self.root / "manifest.json"
        self.payload = {
            "version": 1, "source_ref": "fixture",
            "scope": "source-only-development-review",
            "launch_authorized": False,
            "telegram_egress_authorized": False,
            "whatsapp_enabled": False,
            "artifacts": [{"path": "safe/candidate.txt", "git_blob": verifier.git_blob(self.source)}],
        }
        self.write_manifest()

    def write_manifest(self):
        self.manifest.write_text(json.dumps(self.payload), encoding="utf-8")

    def test_known_git_blob_digest(self):
        data = b"fixture-only"
        expected = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        self.assertEqual(verifier.git_blob(self.source), expected)

    def test_valid_inert_manifest_passes(self):
        self.assertEqual(verifier.verify(self.root, self.manifest), 1)

    def test_modified_source_is_rejected(self):
        self.source.write_bytes(b"fixture-changed")
        with self.assertRaisesRegex(ValueError, "Source bytes changed"):
            verifier.verify(self.root, self.manifest)

    def test_egress_or_launch_enabled_is_rejected(self):
        for key in ("launch_authorized", "telegram_egress_authorized", "whatsapp_enabled"):
            with self.subTest(key=key):
                self.payload[key] = True
                self.write_manifest()
                with self.assertRaisesRegex(ValueError, "inert"):
                    verifier.verify(self.root, self.manifest)
                self.payload[key] = False

    def test_path_traversal_duplicate_and_symlinks_rejected(self):
        self.payload["artifacts"][0]["path"] = "../safe/candidate.txt"
        self.write_manifest()
        with self.assertRaises(ValueError):
            verifier.verify(self.root, self.manifest)
        self.payload["artifacts"][0]["path"] = "safe/candidate.txt"
        self.payload["artifacts"].append(dict(self.payload["artifacts"][0]))
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            verifier.verify(self.root, self.manifest)
        self.payload["artifacts"].pop()
        (self.root / "alias").symlink_to(self.root / "safe", target_is_directory=True)
        self.payload["artifacts"][0]["path"] = "alias/candidate.txt"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "Symbolic"):
            verifier.verify(self.root, self.manifest)


if __name__ == "__main__":
    unittest.main()
