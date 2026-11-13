"""Focused runner preflight checks; no Docker or private-file access."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).parent / 'integration/focused_application_runner.py'
SPEC = importlib.util.spec_from_file_location('focused_application_runner', PATH)
focused = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(focused)


class FocusedRunnerTests(unittest.TestCase):
    def test_terse_and_verbose_sqlstates_preserve_negative_assertions(self):
        for state in ('42501','22023','55000','23505','42702','42P01','P0001'):
            for error in ('ERROR:  '+state, 'ERROR:  '+state+': suppressed test detail'):
                with self.subTest(state=state,error_format=error.endswith('detail')):
                    self.assertEqual(focused.sqlstate_from_error(error).group(1),state)
        self.assertIsNone(focused.sqlstate_from_error('ERROR: invalid format'))
        self.assertIsNone(focused.sqlstate_from_error('ERROR: 42501suffix'))

    def test_missing_execution_approval_stops_before_execute(self):
        args = ['runner', '--baseline', '/unused', '--expected-daemon-id', 'synthetic',
                '--case', 'legacy-concurrency']
        with patch.object(sys, 'argv', args), patch.object(focused, 'execute') as execute, patch('builtins.print'):
            self.assertEqual(focused.main(), 1)
        execute.assert_not_called()

    def test_symlink_and_unknown_case_stop_before_docker(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'synthetic.sql'
            source.write_text('SELECT 1;')
            link = Path(directory) / 'link.sql'
            link.symlink_to(source)
            with patch.object(focused.subprocess, 'run') as command:
                for baseline, cases in (
                    (link, ['legacy-concurrency']), (source, ['../unapproved.sql']),
                    (source, ['reminder_recovery.sql', 'reminder_recovery.sql']),
                    (source, ['legacy-concurrency', 'legacy_coexistence.sql']),
                    (source, ['restart-recovery', 'reminder_recovery.sql']),
                    (source, ['reconciliation', 'restart-recovery']),
                    (source, ['lunar', 'reminder_recovery.sql']),
                    (source, ['lunar', 'lunar']),
                ):
                    with self.subTest(cases=cases), self.assertRaises(focused.Failure):
                        focused.execute(baseline, 'synthetic', cases)
            command.assert_not_called()

    def test_wrong_daemon_stops_before_image_or_container_operations(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'synthetic.sql'
            source.write_text('SELECT 1;')
            result = subprocess.CompletedProcess([], 0, json.dumps({'ID': 'wrong'}), '')
            for cases in (['legacy-concurrency'], ['lunar']):
                with patch.object(focused.subprocess, 'run', return_value=result) as command:
                    with self.assertRaises(focused.Failure):
                        focused.execute(source, 'synthetic', cases)
                command.assert_called_once()
                self.assertEqual(command.call_args.args[0][-3:], ['info', '--format', '{{json .}}'])
