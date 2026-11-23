import contextlib
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch

import httpx

path = Path(__file__).parent / "integration/beta_relay_journey.py"
spec = importlib.util.spec_from_file_location("beta_journey", path)
journey = importlib.util.module_from_spec(spec)
spec.loader.exec_module(journey)


class RelayDiagnosticsTests(unittest.TestCase):
    def response(self, status, body):
        return httpx.Response(status, json=body, request=httpx.Request("POST", "http://fixture.invalid"))

    def test_expected_denial_requires_exact_body_and_status(self):
        for status in (200, 403):
            self.assertEqual(journey.decode(self.response(status, {"status": "denied"}), denial=True),
                             {"status": "denied"})
            for body in ({}, {"status": "active"}, {"status": "denied", "token": "secret"}):
                with self.assertRaises(journey.DenialMismatch):
                    journey.decode(self.response(status, body), denial=True)
        for status in (401, 500):
            with self.assertRaises(httpx.HTTPStatusError):
                journey.decode(self.response(status, {"status": "denied"}), denial=True)
        with self.assertRaises(httpx.HTTPStatusError):
            journey.decode(self.response(403, {"status": "denied"}))

    def test_install_failure_identifies_only_safe_fields(self):
        stages = ["/healthz/readiness", "/rest/owner/setup", "/rest/workflows", "/rest/workflows/1/activate"]
        names = ["n8n_health", "n8n_owner_setup", "n8n_workflow_create", "n8n_workflow_activate"]
        for endpoint, name in zip(stages, names):
            def reply(request):
                return httpx.Response(503 if request.url.path == endpoint else 200,
                                      json={"data": {"id": "1", "versionId": "private-fixture"}})
            with httpx.Client(base_url="http://fixture.invalid", transport=httpx.MockTransport(reply)) as client:
                # install owns its client context
                from unittest.mock import MagicMock
                factory = MagicMock()
                factory.return_value.__enter__.return_value = client
                output = io.StringIO()
                with patch.object(journey.httpx, "Client", factory), patch.object(journey.time, "sleep"), contextlib.redirect_stderr(output):
                    self.assertEqual(journey.run(journey.install), 1)
                self.assertEqual(output.getvalue(), f"RELAY_FAIL step={name} class=HTTPStatusError http=503\n")
