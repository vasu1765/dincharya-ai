"""Exercise the native runner's failure and cleanup paths with offline executables."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tests/integration/beta_native.sh"


class NativeDiagnosticsTests(unittest.TestCase):
    def run_failure(self, ordinal, expected_stage, drift=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def executable(name, script):
                path = root / name
                path.write_text("#!/usr/bin/env bash\nset -eu\n" + script)
                path.chmod(0o700)

            executable("git", """
case "$1" in
rev-parse) echo "$REV";;
status) ;;
archive) tar -cf - --files-from /dev/null;;
esac
""")
            executable("docker", """
case "$*" in
info*) echo 44c1ef83-c50e-4ecc-8f19-4b112bc40f29;;
"image inspect"*) echo "${!#}";;
"network create"*) echo fixture-net;;
run*"beta_relay_journey.py")
  if [[ $FAIL_AT == relay ]]; then
    echo 'PRIVATE_FIXTURE signature' >&2
    echo 'RELAY_FAIL step=pause_apply class=AssertionError http=0' >&2
    exit 1
  fi;;
run*) echo fixture-container;;
*"cat /proc/1/comm") echo postgres;;
*"psql "*"-f -")
  cat >/dev/null
  n=0
  if [[ -f $COUNT ]]; then read -r n < "$COUNT"; fi
  echo "$((++n))" > "$COUNT"
  if [[ $n == "$FAIL_AT" ]]; then
    echo 'psql:<stdin>:42: ERROR:  42501: PRIVATE_FIXTURE_MESSAGE' >&2
    echo 'DETAIL: PRIVATE_FIXTURE_DETAIL' >&2
    exit 3
  fi;;
"ps -aq"*) echo owned;;
"rm -fv owned") touch "$CLEANED";;
"volume ls -q") if [[ -f $CLEANED && $DRIFT == yes ]]; then echo unexpected; fi;;
esac
""")
            image = "sha256:" + "1" * 64
            cleaned = root / "cleaned"
            env = dict(os.environ, PATH=directory + ":" + os.environ["PATH"], REV="a"*40,
                       PG=image, APP=image, N8N=image, COUNT=str(root/"count"),
                       FAIL_AT=str(ordinal), DRIFT="yes" if drift else "no", CLEANED=str(cleaned))
            result = subprocess.run(["bash", str(RUNNER)], cwd=ROOT, env=env,
                                    capture_output=True, text=True, timeout=10)
            output = result.stdout + result.stderr
            if ordinal == "relay":
                self.assertEqual(result.returncode, 1, output)
                self.assertIn("RELAY_FAIL step=pause_apply class=AssertionError http=0", output)
                self.assertIn("FAIL stage=signed_relay_journey exit=1", output)
                self.assertNotIn("PRIVATE_FIXTURE", output)
                self.assertIn("PASS cleanup and unchanged Docker inventory", output)
                return
            self.assertEqual(result.returncode, 3, output)
            self.assertIn(f"FAIL stage={expected_stage} exit=3 sqlstate=42501 input_line=42", output)
            self.assertNotIn("PRIVATE_FIXTURE", output)
            self.assertTrue(cleaned.exists())
            self.assertIn("FAIL inventory volumes" if drift else "PASS cleanup and unchanged Docker inventory", output)
            self.assertNotIn("STAGE pg_dump", output)

    def test_relay_marker_survives_cleanup(self):
        self.run_failure("relay", "signed_relay_journey")

    def test_bootstrap_exit_three(self):
        self.run_failure(1, "schema_bootstrap")

    def test_role_setup_exit_three(self):
        self.run_failure(2, "gateway_role_setup")

    def test_assertion_failure_survives_inventory_failure(self):
        self.run_failure(3, "sql_assertions", drift=True)
