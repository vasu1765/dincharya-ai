"""Offline runner regressions: no Docker commands or service connections."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parent / 'integration/runner.py'
spec = importlib.util.spec_from_file_location('integration_runner', PATH)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def payload(node, value):
    return {'data': {'resultData': {'runData': {
        node: [{'executionStatus': 'success', 'data': {'main': [[{'json': value}]]}}]
    }}}}


def scheduled(stamp='2026-01-01T00:00:00Z'):
    result = payload('Synthetic output', {'result': 'synthetic-state-only'})
    result['data']['resultData']['runData'].update(
        payload('Synthetic schedule', {'timestamp': stamp})['data']['resultData']['runData'])
    return result


def workflow(last=30000000):
    return {'active': True, 'settings': {'timezone': 'Asia/Kolkata'},
            'nodes': [{'type': 'n8n-nodes-base.scheduleTrigger', 'parameters': {
                'rule': {'interval': [{'field': 'minutes', 'minutesInterval': 7}]}}}],
            'staticData': {'node:Synthetic schedule': {'recurrenceRules': [last],
                                                     'recurrenceRuleSignatures': ['minutes:7']}}}


class RunnerTests(unittest.TestCase):
    def test_manual_requires_actual_expected_output(self):
        r.validate_manual(payload('Reply', {'reply': 'synthetic-pass'}))
        for value in ({'reply': 'wrong'}, {'other': 'synthetic-pass'}):
            with self.subTest(value=value), self.assertRaises(r.Failure):
                r.validate_manual(payload('Reply', value))

    def test_manual_errors_and_unfinished_execution_fail(self):
        data = payload('Reply', {'reply': 'synthetic-pass'})
        data['data']['resultData']['error'] = {'message': 'synthetic-pass'}
        with self.assertRaises(r.Failure): r.validate_manual(data)
        for key, value in [('status', 'error'), ('finished', False)]:
            data = payload('Reply', {'reply': 'synthetic-pass'})
            data[key] = value
            with self.assertRaises(r.Failure): r.validate_manual(data)

    def test_node_error_fails_despite_expected_output(self):
        data = payload('Reply', {'reply': 'synthetic-pass'})
        data['data']['resultData']['runData']['Reply'][0]['error'] = {'message': 'failed'}
        with self.assertRaises(r.Failure): r.validate_manual(data)

    def test_cli_requires_complete_structured_result(self):
        value = payload('Reply', {'reply': 'synthetic-pass'})
        self.assertEqual(r.parse_cli_result('startup\n' + json.dumps(value)), value)
        for text in ('synthetic-pass', json.dumps(value) + '\nerror', '{}'):
            with self.subTest(text=text), self.assertRaises(r.Failure): r.parse_cli_result(text)

    def test_successful_schedule_requires_expected_outputs(self):
        rows = [{'id': '1', 'status': 'success', 'mode': 'trigger'}]
        self.assertEqual(r.validate_emissions(rows, {'1': scheduled()}), 1)
        bad = scheduled()
        bad['data']['resultData']['runData']['Synthetic output'][0]['data']['main'][0][0]['json']['result'] = 'wrong'
        with self.assertRaises(r.Failure): r.validate_emissions(rows, {'1': bad})
        with self.assertRaises(r.Failure): r.validate_emissions(rows, {})

    def test_count_growth_does_not_hide_execution_errors(self):
        for status in ('error', 'crashed', 'canceled', 'waiting', 'unknown'):
            with self.subTest(status=status), self.assertRaises(r.Failure):
                r.validate_emissions([{'id': '1', 'status': status, 'mode': 'trigger'}], {})

    def test_pending_execution_is_not_success(self):
        self.assertEqual(r.validate_emissions([{'id': '1', 'status': 'running', 'mode': 'trigger'}], {}), 0)

    def test_duplicate_slot_fails_even_with_distinct_execution_ids(self):
        rows = [{'id': str(i), 'status': 'success', 'mode': 'trigger'} for i in (1, 2)]
        with self.assertRaisesRegex(r.Failure, 'Duplicate scheduled'):
            r.validate_emissions(rows, {'1': scheduled(), '2': scheduled('2026-01-01T00:00:01Z')})

    def test_distinct_slots_pass_across_restart_window(self):
        rows = [{'id': str(i), 'status': 'success', 'mode': 'trigger'} for i in (1, 2)]
        self.assertEqual(r.validate_emissions(rows, {
            '1': scheduled(), '2': scheduled('2026-01-01T00:00:05Z')}), 2)

    def test_duplicate_identity_and_manual_mode_rejected(self):
        row = {'id': '1', 'status': 'success', 'mode': 'trigger'}
        with self.assertRaises(r.Failure): r.validate_emissions([row, row], {'1': scheduled()})
        with self.assertRaises(r.Failure):
            r.validate_emissions([{**row, 'mode': 'manual'}], {'1': scheduled()})

    def test_bad_or_missing_emission_timestamp_rejected(self):
        for value in (None, 'bad', '2026-01-01T00:00:00'):
            with self.subTest(value=value), self.assertRaises(r.Failure): r.timestamp(value)

    def test_restart_allows_advancing_or_equal_last_run(self):
        before = r.scheduler_snapshot(workflow())
        r.validate_restart(before, r.scheduler_snapshot(workflow()))
        r.validate_restart(before, r.scheduler_snapshot(workflow(30000007)))

    def test_restart_rejects_lost_or_regressed_state(self):
        with self.assertRaises(r.Failure):
            r.validate_restart(r.scheduler_snapshot(workflow()), r.scheduler_snapshot(workflow(29000000)))
        for state in ({}, {'recurrenceRules': [], 'recurrenceRuleSignatures': ['minutes:7']},
                      {'recurrenceRules': [float('nan')], 'recurrenceRuleSignatures': ['minutes:7']},
                      {'recurrenceRules': [True], 'recurrenceRuleSignatures': ['minutes:7']}):
            value = workflow()
            value['staticData']['node:Synthetic schedule'] = state
            with self.subTest(state=state), self.assertRaises(r.Failure): r.scheduler_snapshot(value)

    def test_restart_requires_configuration_timezone_signature(self):
        for modify in ('interval', 'timezone', 'signature', 'active'):
            value = workflow()
            if modify == 'interval': value['nodes'][0]['parameters']['rule']['interval'][0]['minutesInterval'] = 10
            if modify == 'timezone': value['settings']['timezone'] = 'UTC'
            if modify == 'signature': value['staticData']['node:Synthetic schedule']['recurrenceRuleSignatures'] = []
            if modify == 'active': value['active'] = False
            with self.subTest(modify=modify), self.assertRaises(r.Failure): r.scheduler_snapshot(value)

    def test_bounded_wait_has_clear_timeout(self):
        ticks = iter([0, 0, 2, 4])
        with self.assertRaisesRegex(r.Failure, 'Timed out waiting for synthetic readiness'):
            r.bounded_wait(lambda: False, 'synthetic readiness', timeout=3,
                           clock=lambda: next(ticks), sleep=lambda _: None)

    def test_wait_returns_success_and_propagates_errors(self):
        self.assertEqual(r.bounded_wait(lambda: 'ready', 'ready'), 'ready')
        with self.assertRaisesRegex(r.Failure, 'unexpected'):
            r.bounded_wait(lambda: r.require(False, 'unexpected'), 'readiness')

    def test_client_environment_drops_credentials_home_and_proxies(self):
        parent = {'HOME': '/private', 'PATH': '/untrusted', 'DOCKER_CONFIG': '/private/docker',
                  'HTTP_PROXY': 'private', 'COMPOSE_FILE': 'production', 'TOKEN': 'private'}
        with patch('pathlib.Path.open', side_effect=AssertionError('No file access')):
            env = r.client_environment(parent, '/tmp/isolated')
        self.assertEqual(env['HOME'], '/tmp/isolated')
        self.assertEqual(env['DOCKER_CONFIG'], '/tmp/isolated')
        self.assertEqual(env['DOCKER_HOST'], r.ENDPOINT)
        for key in ('TOKEN', 'HTTP_PROXY', 'COMPOSE_FILE'): self.assertNotIn(key, env)

    def test_remote_context_host_and_tls_overrides_rejected(self):
        for key, value in [('DOCKER_HOST', 'tcp://remote:2375'), ('DOCKER_HOST', ''),
                           ('DOCKER_CONTEXT', 'remote'), ('DOCKER_TLS_VERIFY', '1'),
                           ('DOCKER_CERT_PATH', '/private')]:
            with self.subTest(key=key), self.assertRaises(r.Failure):
                r.client_environment({key: value}, '/tmp/isolated')

    def test_explicit_local_endpoint_and_default_context_allowed(self):
        env = r.client_environment({'DOCKER_HOST': r.ENDPOINT, 'DOCKER_CONTEXT': 'default'}, '/tmp/isolated')
        self.assertNotIn('DOCKER_CONTEXT', env)

    def test_daemon_identity_must_match_local_desktop_and_operator_pin(self):
        info = {'ID': 'test-daemon', 'OperatingSystem': 'Docker Desktop', 'Name': 'docker-desktop', 'OSType': 'linux'}
        r.validate_daemon(info, 'test-daemon')
        for key, value in [('ID', 'other'), ('OperatingSystem', 'Ubuntu'), ('Name', 'remote'), ('OSType', 'windows')]:
            with self.subTest(key=key), self.assertRaises(r.Failure):
                r.validate_daemon({**info, key: value}, 'test-daemon')

    def test_compose_definition_passes_review_pin(self):
        r.validate_configuration(json.loads((r.HERE / 'compose.json').read_text()))

    def test_modified_compose_rejected_before_docker(self):
        original = json.loads((r.HERE / 'compose.json').read_text())
        for key, value in [('ports', ['5678:5678']), ('privileged', True),
                           ('network_mode', 'host'), ('env_file', ['../../.env'])]:
            config = copy.deepcopy(original)
            config['services']['n8n-test'][key] = value
            with self.subTest(key=key), self.assertRaises(r.Failure): r.validate_configuration(config)
        config = copy.deepcopy(original)
        config['services']['n8n-test']['environment']['DB_POSTGRESDB_HOST'] = 'production'
        with self.assertRaises(r.Failure): r.validate_configuration(config)

    def test_docker_command_pins_host_config_and_compose_project(self):
        runner = r.Runner(r.client_environment({}, '/tmp/test-config'))
        with patch.object(r.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as call:
            runner.compose('restart', 'n8n-test')
        args = call.call_args.args[0]
        self.assertEqual(args[:5], ['docker', '--config', '/tmp/test-config', '--host', r.ENDPOINT])
        for value in ('--env-file', '/dev/null', r.PROJECT): self.assertIn(value, args)
        self.assertEqual(args[-2:], ['restart', 'n8n-test'])
        self.assertEqual(call.call_args.kwargs['timeout'], 45)

    def test_command_failure_and_timeout_do_not_expose_raw_output(self):
        runner = r.Runner(r.client_environment({}, '/tmp/test-config'))
        with patch.object(r.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, 'PRIVATE', 'SECRET')):
            with self.assertRaises(r.Failure) as error: runner.command(['info'])
        self.assertNotIn('SECRET', str(error.exception))
        with patch.object(r.subprocess, 'run', side_effect=subprocess.TimeoutExpired('private', 45)):
            with self.assertRaisesRegex(r.Failure, 'bounded timeout'): runner.command(['info'])

    def test_non_test_database_rejected_without_commands(self):
        runner = r.Runner(r.client_environment({}, '/tmp/test-config'))
        with patch.object(r.subprocess, 'run', side_effect=AssertionError('Docker forbidden')):
            with self.assertRaises(r.Failure): runner.sql('SELECT 1', 'production')


class CleanupTests(unittest.TestCase):
    def fake_runner(self):
        from unittest.mock import MagicMock
        runner = MagicMock()
        runner.env = {}
        runner.password = 'synthetic-only'
        runner.command.side_effect = lambda args: 'original-id' if args == ['ps', '-q'] else ''
        daemon = {'ID': 'test-daemon', 'OperatingSystem': 'Docker Desktop',
                  'Name': 'docker-desktop', 'OSType': 'linux'}
        def metadata(args):
            if args[0] == 'info': return daemon
            image = args[-1]
            return [{'Id': image, 'Config': {'Labels': {'org.opencontainers.image.version': '2.47.3'}}}]
        runner.json_command.side_effect = metadata
        return runner

    def execute_fake(self, runner):
        from types import SimpleNamespace
        import stat
        def make_runner(env):
            runner.env = env
            runner.config_path = env['DOCKER_CONFIG']
            return runner
        with patch.dict(r.os.environ, {}, clear=True), \
             patch.object(r, 'Runner', side_effect=make_runner), \
             patch.object(r.os, 'stat', wraps=r.os.stat) as metadata:
            # Preserve normal stat for fixture and temporary-directory operations.
            real_stat = metadata._mock_wraps
            def socket_stat(path, *args, **kwargs):
                if str(path) == '/var/run/docker.sock': return SimpleNamespace(st_mode=stat.S_IFSOCK)
                return real_stat(path, *args, **kwargs)
            metadata.side_effect = socket_stat
            with patch('builtins.print'):
                r.execute('test-daemon')

    def test_success_cleans_project_and_ephemeral_client_config(self):
        runner = self.fake_runner()
        self.execute_fake(runner)
        self.assertEqual(runner.compose.call_args_list[-1].args, ('down', '--timeout', '20'))
        self.assertEqual(runner.password, '')
        self.assertEqual(runner.env, {})
        self.assertFalse(Path(runner.config_path).exists())
        runner.isolation.assert_called_once()
        runner.tests.assert_called_once()

    def test_partial_start_failure_still_attempts_cleanup(self):
        runner = self.fake_runner()
        runner.compose.side_effect = [r.Failure('start failed'), '']
        with self.assertRaisesRegex(r.Failure, 'start failed'): self.execute_fake(runner)
        self.assertEqual(runner.compose.call_args_list[-1].args, ('down', '--timeout', '20'))
        self.assertEqual(runner.env, {})
        runner.tests.assert_not_called()

    def test_interruption_still_attempts_cleanup(self):
        runner = self.fake_runner()
        runner.tests.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt): self.execute_fake(runner)
        self.assertEqual(runner.compose.call_args_list[-1].args, ('down', '--timeout', '20'))
        self.assertEqual(runner.password, '')

    def test_cleanup_failure_is_fatal_and_still_clears_secret_references(self):
        runner = self.fake_runner()
        runner.compose.side_effect = ['', r.Failure('cleanup failed')]
        with self.assertRaisesRegex(r.Failure, 'cleanup failed'): self.execute_fake(runner)
        self.assertEqual(runner.env, {})
        self.assertEqual(runner.password, '')

    def test_preexisting_project_is_never_started_or_deleted(self):
        runner = self.fake_runner()
        runner.command.return_value = 'existing-test-container'
        runner.command.side_effect = None
        with self.assertRaisesRegex(r.Failure, 'already has containers'): self.execute_fake(runner)
        runner.compose.assert_not_called()


class ImportContractTests(unittest.TestCase):
    def runner(self, imported=None, persisted=None):
        from unittest.mock import MagicMock
        runner = r.Runner(r.client_environment({}, '/tmp/test-config'))
        runner.api = MagicMock(return_value={'ids': {'manual-smoke': 'manual', 'scheduler-state': 'schedule'},
                                             'importedState': imported, 'nativeState': {'synthetic': True}})
        expected = json.loads((r.HERE / 'fixtures/scheduler-state.json').read_text())['staticData']
        runner.workflow = MagicMock(side_effect=[{'staticData': None},
                                                 {'staticData': expected if persisted is None else persisted},
                                                 {'staticData': {'synthetic': True}}])
        runner.compose = MagicMock()
        return runner

    def test_native_cli_must_preserve_unchanged_state_after_api_drops_it(self):
        runner = self.runner()
        with patch('builtins.print'): runner.import_workflows()
        self.assertIn('import:workflow', runner.compose.call_args.args)
        self.assertIn('N8N_RUNNERS_BROKER_PORT=5680', runner.compose.call_args.args)
        self.assertIn('--input=/tmp/synthetic-scheduler-import.json', runner.compose.call_args.args)

    def test_changed_api_contract_stops_before_cli_import(self):
        runner = self.runner(imported={'unexpected': True})
        with self.assertRaisesRegex(r.Failure, 'API state behavior changed'): runner.import_workflows()
        runner.compose.assert_not_called()

    def test_cli_dropping_state_is_a_failure(self):
        runner = self.runner(persisted={})
        with patch('builtins.print'), self.assertRaisesRegex(r.Failure, 'CLI import did not preserve'):
            runner.import_workflows()


class ApiSessionTests(unittest.TestCase):
    def test_session_reuse_restart_login_and_http_errors_without_services(self):
        import shutil
        node = shutil.which('node')
        if node is None: self.skipTest('Node unavailable for offline VM regression')
        result = subprocess.run([node, str(r.HERE / 'test-api-client.js'), str(r.HERE / 'api-client.js')],
                                capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


class DurableSchedulerTests(unittest.TestCase):
    def job(self, **changes):
        return {**{'id': 'synthetic-job', 'kind': 'interval', 'intervalSeconds': 5,
                   'taskType': 'workflow:schedule-trigger', 'payload': {'workflowId': 'synthetic-workflow'},
                   'nextRunAt': '2026-01-01T00:00:05Z', 'enabled': True}, **changes}

    def test_durable_clock_may_advance_but_job_configuration_must_survive(self):
        before = r.durable_job_snapshot([self.job()], 'synthetic-workflow')
        after = r.durable_job_snapshot([self.job(nextRunAt='2026-01-01T00:00:10Z')], 'synthetic-workflow')
        r.validate_durable_restart(before, after)
        with self.assertRaises(r.Failure): r.validate_durable_restart(after, before)
        changed = r.durable_job_snapshot([self.job(id='replacement-job')], 'synthetic-workflow')
        with self.assertRaises(r.Failure): r.validate_durable_restart(before, changed)

    def test_wrong_owner_missing_clock_and_wrong_interval_fail(self):
        for changes in ({'payload': {'workflowId': 'other'}}, {'nextRunAt': None},
                        {'intervalSeconds': 6}, {'taskType': 'other'}, {'enabled': False}, {'orphanedAt': 'unexpected'}):
            with self.subTest(changes=changes), self.assertRaises(r.Failure):
                r.durable_job_snapshot([self.job(**changes)], 'synthetic-workflow')
        with self.assertRaises(r.Failure): r.durable_job_snapshot([], 'synthetic-workflow')

    def test_seven_minute_rule_requires_actual_durable_interval(self):
        r.durable_job_snapshot([self.job(intervalSeconds=420)], 'synthetic-workflow', native=True)
        with self.assertRaises(r.Failure):
            r.durable_job_snapshot([self.job()], 'synthetic-workflow', native=True)

    def test_persistent_task_identity_is_independent_of_advancing_job_clock(self):
        task = {'id': 'task-1', 'jobId': 'job-1', 'scheduledFor': '2026-01-01T00:00:00Z', 'status': 'completed'}
        result = r.durable_tasks_snapshot([task])
        self.assertEqual(result['task-1'][0], 'job-1')
        with self.assertRaises(r.Failure):
            r.durable_tasks_snapshot([task, {**task, 'id': 'task-2'}])
        for changes in ({'status': 'failed'}, {'status': 'expired'},
                        {'errorMessage': 'invented failure'}, {'attempts': 2}):
            with self.subTest(changes=changes), self.assertRaises(r.Failure):
                r.durable_tasks_snapshot([{**task, **changes}])

    def test_imported_legacy_arrays_survive_without_claiming_durable_engine_updates_them(self):
        before = r.scheduler_snapshot(workflow(12345))
        r.validate_restart(before, r.scheduler_snapshot(workflow(12345)))


if __name__ == '__main__':
    unittest.main()
