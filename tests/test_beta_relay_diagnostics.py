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


class WebhookReadinessTests(unittest.TestCase):
    def probe(self, responses):
        requests = []
        def reply(request):
            requests.append(request)
            status, body = responses[len(requests)-1]
            return httpx.Response(status, json=body)
        with httpx.Client(transport=httpx.MockTransport(reply)) as client, \
                patch.object(journey.time, "sleep") as sleep:
            result = journey.wait_for_webhook(client, lambda stage: None,
                                               attempts=len(responses), delay=0)
        return result, requests, sleep.call_count

    def test_activation_race_waits_only_for_registration_then_exact_denial(self):
        for status in (200, 403):
            result, requests, sleeps = self.probe([
                (404, {"message": "not registered"}),
                (404, {"message": "not registered"}),
                (status, {"status": "denied"})])
            self.assertEqual(result, {"status": "denied"})
            self.assertEqual(sleeps, 2)
            import json
            for request in requests:
                self.assertEqual(json.loads(request.content), {})
                self.assertEqual(request.headers['x-dincharya-signature'], 'readiness-invalid')

    def test_never_retries_authentication_server_or_malformed_denials(self):
        for status, body, error in [
                (401, {"status": "denied"}, httpx.HTTPStatusError),
                (500, {"status": "denied"}, httpx.HTTPStatusError),
                (200, {"status": "active"}, journey.DenialMismatch),
                (403, {"status": "denied", "extra": 1}, journey.DenialMismatch)]:
            calls = []
            def reply(request):
                calls.append(request)
                return httpx.Response(status, json=body)
            with httpx.Client(transport=httpx.MockTransport(reply)) as client, \
                    patch.object(journey.time, "sleep") as sleep:
                with self.assertRaises(error):
                    journey.wait_for_webhook(client, lambda _: None)
                self.assertEqual(len(calls), 1)
                sleep.assert_not_called()

    def test_registration_timeout_is_failure_not_security_acceptance(self):
        calls = []
        def reply(request):
            calls.append(request)
            return httpx.Response(404, json={"message": "not registered"})
        with httpx.Client(transport=httpx.MockTransport(reply)) as client, \
                patch.object(journey.time, "sleep") as sleep:
            with self.assertRaises(httpx.HTTPStatusError):
                journey.wait_for_webhook(client, lambda _: None, attempts=3, delay=0)
            self.assertEqual(len(calls), 3)
            self.assertEqual(sleep.call_count, 2)

    def test_probe_is_rejected_before_database_connection(self):
        connect = unittest.mock.Mock(side_effect=AssertionError("must not connect"))
        dispatcher = journey.BetaDispatcher(connect, 'synthetic-key-'*4)
        self.assertEqual(dispatcher.handle({}, 'readiness-invalid'), {"status": "denied"})
        connect.assert_not_called()

    def test_readiness_failure_has_own_secret_safe_substage(self):
        output = io.StringIO()
        with httpx.Client(transport=httpx.MockTransport(
                lambda request: httpx.Response(404, json={}))) as client, \
                patch.object(journey.time, 'sleep'), contextlib.redirect_stderr(output):
            self.assertEqual(journey.run(lambda mark: journey.wait_for_webhook(
                client, mark, attempts=1)), 1)
        self.assertEqual(output.getvalue(),
                         'RELAY_FAIL step=relay_webhook_readiness class=HTTPStatusError http=404\n')
