"""Offline bootstrap diagnostics and supervised stop regression cases."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BootstrapTests(unittest.TestCase):
    def invoke(self, status, diagnostic):
        with tempfile.TemporaryDirectory() as directory:
            migration = Path(directory, "0004_recording_budget.sql")
            migration.write_text("select 1;\n")
            return subprocess.run(
                ["bash", "-c", """
set -eu
source tests/personal_migration_diagnostic.sh
sql() {
  [[ "$*" == "-v VERBOSITY=verbose -f -" ]] || return 91
  cat >/dev/null
  printf '%s\\n' "$DIAGNOSTIC" >&2
  return "$STATUS"
}
run_personal_migration "$1"
""", "fixture", str(migration)], cwd=ROOT,
                env={**os.environ, "STATUS":str(status), "DIAGNOSTIC":diagnostic},
                text=True, capture_output=True)

    def test_exit_three_and_redaction(self):
        result = self.invoke(3, "psql:<stdin>:26: ERROR:  42601: private error text\n"
                                "LINE 4: private SQL with a secret\nDETAIL: private data")
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "FAIL migration=0004_recording_budget.sql exit=3 "
                                       "sqlstate=42601 input_line=26 statement_line=4\n")

    def test_transport_failure_without_state(self):
        result = self.invoke(125, "sensitive connection detail")
        self.assertEqual(result.returncode, 125)
        self.assertEqual(result.stderr, "FAIL migration=0004_recording_budget.sql exit=125 "
                                       "sqlstate=unknown input_line=unknown statement_line=unknown\n")

    def test_success_suppresses_notices(self):
        result = self.invoke(0, "NOTICE: private synthetic value")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_all_three_function_bodies_are_delimited(self):
        sql = (ROOT/"database/personal/0004_recording_budget.sql").read_text()
        functions = re.split(r"(?m)^CREATE FUNCTION beta\.", sql)[1:]
        self.assertEqual(len(functions), 3)
        for definition in functions:
            with self.subTest(function=definition.split("(")[0]):
                self.assertRegex(definition, r"(?ms) AS \$\$\n.+?^(?:END )?\$\$;")
                self.assertEqual(definition.count("$$"), 2)

    def test_stop_arriving_during_health_probe_is_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            python = root/"python"
            python.write_text("""#!/usr/bin/env bash
if [[ $2 == dincharya.personal_service ]]; then
  trap 'exit 0' TERM
  while [[ ! -e "$5/STOP" ]]; do sleep .05; done
elif [[ ! -e "$4/ready" ]]; then
  touch "$4/ready"
else
  touch "$4/STOP"
  exit 1
fi
""")
            python.chmod(0o700)
            result = subprocess.run(["bash","scripts/supervise-personal-recording.sh","--recorded-root",directory],
                cwd=ROOT, input="", text=True, capture_output=True, timeout=10,
                env={**os.environ,"PATH":directory+":"+os.environ["PATH"]})
            self.assertTrue((root/"STOP").exists())
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
