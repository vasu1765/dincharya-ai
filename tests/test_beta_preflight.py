"""Offline, no-network tests of beta preparation safety checks."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from dincharya.beta_preflight import validate_plan, verify_file

PLAN = Path(__file__).resolve().parents[1] / "docs" / "beta-runtime-plan.json"


class BetaPreflightTests(unittest.TestCase):
    def setUp(self):
        self.good = json.loads(PLAN.read_text(encoding="utf-8"))

    def test_offline_preparation_plan(self):
        self.assertTrue(validate_plan(self.good))

    def test_any_messaging_startup_or_source_promotion_rejected(self):
        for key in ("telegram_egress", "whatsapp", "startup", "source_adopted"):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.good)
                changed[key] = True
                with self.assertRaises(ValueError):
                    validate_plan(changed)

    def test_unpinned_mutable_images_and_unreviewed_services_rejected(self):
        for img in ("postgres:17", "n8n:latest", "", None, "sha256:not-a-digest"):
            with self.subTest(img=img):
                changed = copy.deepcopy(self.good)
                changed["services"]["postgres"]["image"] = img
                with self.assertRaises(ValueError):
                    validate_plan(changed)
        changed = copy.deepcopy(self.good)
        changed["services"]["worker"]["enabled"] = True
        with self.assertRaises(ValueError):
            validate_plan(changed)
        changed = copy.deepcopy(self.good)
        del changed["services"]["scheduler"]
        with self.assertRaises(ValueError):
            validate_plan(changed)

    def test_reused_database_or_false_restoration_claim_rejected(self):
        for key, value in (("name", "dincharya_app_test"),
                           ("fresh", False), ("isolated", False),
                           ("migration_adopted", True)):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.good)
                changed["database"][key] = value
                with self.assertRaises(ValueError):
                    validate_plan(changed)
        changed = copy.deepcopy(self.good)
        changed["backup"]["restore_verified"] = True
        with self.assertRaises(ValueError):
            validate_plan(changed)

    def test_secret_fields_and_unknown_flags_rejected(self):
        changed = copy.deepcopy(self.good)
        changed["telegram_token"] = "would-be-secret"
        with self.assertRaises(ValueError):
            validate_plan(changed)
        changed = copy.deepcopy(self.good)
        changed["allow_network"] = True
        with self.assertRaises(ValueError):
            validate_plan(changed)

    def test_readonly_file_verifier_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "plan.json"
            real.write_text(json.dumps(self.good), encoding="utf-8")
            self.assertTrue(verify_file(real))
            link = root / "link.json"
            link.symlink_to(real)
            with self.assertRaisesRegex(ValueError, "Unsafe plan"):
                verify_file(link)


if __name__ == "__main__":
    unittest.main()
