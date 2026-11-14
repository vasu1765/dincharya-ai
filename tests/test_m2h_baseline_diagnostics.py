"""Offline Cycle 4 launcher regressions; no database or socket connection."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent / "integration"
sys.path.insert(0, str(HERE))
import m2h_baseline_acceptance as acceptance


class BaselineDiagnosticsTests(unittest.TestCase):
    def test_service_socket_is_string_and_readiness_protocol_is_preserved(self):
        config = {"service_socket": "/tmp/synthetic-cycle4-not-created.sock"}
        output = io.StringIO()
        with (patch.object(acceptance, "build_service") as build,
              patch.object(acceptance, "server") as server,
              patch.object(acceptance.threading, "Thread"),
              patch.object(acceptance.Path, "unlink"),
              patch.object(sys, "stdin", io.StringIO(json.dumps(config) + "\nstop\n")),
              contextlib.redirect_stdout(output)):
            acceptance.service_main()
        server.assert_called_once_with(config["service_socket"], build.return_value)
        self.assertEqual(output.getvalue(), '{"ready":true}\n')
        server.return_value.__enter__.return_value.shutdown.assert_called_once()

    def test_stage_failure_never_prints_exception_details(self):
        runner = object.__new__(acceptance.BaselineRunner)
        def fail(*args):
            runner.checkpoint("schema initialization")
            raise RuntimeError("PRIVATE SQL credential path")
        output = io.StringIO()
        with (patch.object(acceptance.M2GRunner, "tests", fail),
              contextlib.redirect_stdout(output), self.assertRaises(RuntimeError)):
            runner.tests()
        self.assertIn("FAIL schema initialization", output.getvalue())
        self.assertNotIn("PRIVATE", output.getvalue())


if __name__ == "__main__":
    unittest.main()
