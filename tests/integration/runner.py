"""Approval-gated synthetic integration runner. Importing this module performs no I/O."""
import argparse
import copy
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import secrets
import signal
import stat
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'tests/integration'
PROJECT = 'dincharya-m2c-synthetic'
NETWORK = PROJECT + '_synthetic-only'
ENDPOINT = 'unix:///var/run/docker.sock'
COMPOSE_DIGEST = '7092ccdca86520b106aeba528b43340842f18f07d0816ab96ea1f05c797f1f22'
IMAGES = {
    'postgres-test': 'sha256:ff87138949ad9a46f32ff23bd6852b52ce024a13dffe9b4087be98292cdd3b4f',
    'n8n-test': 'sha256:6723b440354bb8e1395a1ecee12685fe03923f897bf6e4d5bb2c6c2bd2051697',
}
IMAGES['mock-services'] = IMAGES['n8n-test']
SERVICES = set(IMAGES)


class Failure(RuntimeError):
    """Safe diagnostic with no raw command output or credential values."""


def require(condition, message):
    if not condition:
        raise Failure(message)


def client_environment(parent, directory):
    # Inspect names/values only in memory; never open the user's Docker config/context.
    for key in ('DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'):
        if key in parent:
            permitted = {'DOCKER_HOST': ENDPOINT, 'DOCKER_CONTEXT': 'default'}
            require(parent[key] == permitted.get(key), 'Rejected Docker endpoint/context/TLS override')
    # Drop all inherited Docker/Compose/proxy/API/credential variables, HOME and PATH.
    return {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': str(directory),
            'DOCKER_CONFIG': str(directory), 'DOCKER_HOST': ENDPOINT,
            'LANG': 'C.UTF-8'}


def validate_daemon(info, expected_id):
    require(info.get('ID') == expected_id and bool(expected_id), 'Local daemon ID does not match operator pin')
    require(info.get('OperatingSystem') == 'Docker Desktop' and
            info.get('Name') == 'docker-desktop' and info.get('OSType') == 'linux',
            'Endpoint is not the intended local Linux Docker Desktop daemon')


def validate_configuration(config):
    require(set(config.get('services', {})) == SERVICES and
            config.get('networks') == {'synthetic-only': {'internal': True}} and
            set(config) == {'services', 'networks'}, 'Unexpected Compose resources')
    mounts = {
        'postgres-test': {('./postgres-init.sql', '/docker-entrypoint-initdb.d/010-synthetic.sql')},
        'mock-services': {('./mock-services.js', '/opt/synthetic/mock-services.js')},
        'n8n-test': {('./fixtures/' + name + '.json', '/opt/synthetic/fixtures/' + name + '.json')
                     for name in ('manual-smoke', 'scheduler-state')},
    }
    for name, service in config['services'].items():
        require(service.get('networks') == ['synthetic-only'] and service.get('profiles') == ['integration'] and
                service.get('read_only') is True and service.get('pull_policy') == 'never' and
                service.get('restart') == 'no' and service.get('security_opt') == ['no-new-privileges:true'],
                'Unsafe Compose isolation policy')
        require(not set(service) & {'ports', 'env_file', 'extends', 'privileged', 'network_mode',
                'pid', 'ipc', 'devices', 'build', 'container_name', 'configs', 'secrets', 'volumes_from'},
                'Forbidden Compose capability or external input')
        actual = set()
        for mount in service.get('volumes', []):
            require(mount.get('type') == 'bind' and mount.get('read_only') is True,
                    'Only read-only fixture binds permitted')
            actual.add((mount['source'], mount['target']))
        require(actual == mounts[name], 'Unexpected configured fixture mount')
        for source, _ in actual:
            path = HERE / source
            require(path.resolve().is_relative_to(HERE.resolve()) and not path.is_symlink() and path.is_file(),
                    'Fixture path escaped integration directory')
    # Pin the full reviewed Compose definition, including environments, entrypoints,
    # tmpfs paths, limits and healthchecks. Any change requires a fresh offline review.
    import hashlib
    canonical = json.dumps(config, sort_keys=True, separators=(',', ':')).encode()
    require(hashlib.sha256(canonical).hexdigest() == COMPOSE_DIGEST, 'Compose definition changed since runner review')
    for name in ('manual-smoke', 'scheduler-state'):
        fixture = json.loads((HERE / ('fixtures/' + name + '.json')).read_text())
        require(fixture.get('active') is False, 'Fixture must import inactive')
        for node in fixture['nodes']:
            require(node['type'] in {'n8n-nodes-base.manualTrigger', 'n8n-nodes-base.set',
                                    'n8n-nodes-base.scheduleTrigger'} and 'credentials' not in node,
                    'Fixture contains unapproved node or credentials')


def run_data(value):
    require(isinstance(value, dict), 'Execution payload is not an object')
    require(value.get('status', 'success') == 'success' and value.get('finished', True) is True,
            'Execution did not finish successfully')
    data = value.get('data', value)
    require(isinstance(data, dict), 'Execution data is unavailable')
    result = data.get('resultData')
    require(isinstance(result, dict) and not result.get('error'), 'Execution returned an error or missing result')
    runs = result.get('runData')
    require(isinstance(runs, dict), 'Execution has no node results')
    for entries in runs.values():
        require(isinstance(entries, list) and bool(entries), 'Missing node execution results')
        for entry in entries:
            require(not entry.get('error') and entry.get('executionStatus', 'success') == 'success',
                    'A workflow node did not succeed')
    return runs


def output_items(runs, name):
    require(name in runs and len(runs[name]) == 1, 'Expected exactly one run of ' + name)
    try:
        items = runs[name][0]['data']['main'][0]
        require(isinstance(items, list) and len(items) == 1, 'Expected one output item from ' + name)
        return items[0]['json']
    except (KeyError, IndexError, TypeError):
        raise Failure('Missing output from ' + name) from None


def validate_manual(value):
    runs = run_data(value)
    require(output_items(runs, 'Reply').get('reply') == 'synthetic-pass',
            'Manual smoke did not produce synthetic-pass')


def parse_cli_result(text):
    # n8n may prepend startup messages; require a complete JSON suffix, never substring-match output.
    for index, char in enumerate(text):
        if char != '{':
            continue
        try:
            value, end = json.JSONDecoder().raw_decode(text[index:])
        except ValueError:
            continue
        if not text[index + end:].strip() and isinstance(value, dict) and 'data' in value:
            return value
    raise Failure('Manual CLI returned no complete execution JSON')


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(parsed.tzinfo is not None, 'Emission timestamp lacks timezone')
        return parsed.timestamp()
    except (ValueError, TypeError, AttributeError):
        raise Failure('Invalid scheduler emission timestamp') from None


def validate_emissions(rows, details):
    slots = set()
    ids = set()
    for row in rows:
        require(row['id'] not in ids, 'Duplicate execution identity')
        ids.add(row['id'])
        require(row['mode'] == 'trigger', 'Unexpected execution mode for scheduled workflow')
        require(row['status'] in {'new', 'running', 'success'}, 'Scheduled execution failed or was cancelled')
        if row['status'] != 'success':
            continue
        require(row['id'] in details, 'Successful execution lacks validated output')
        runs = run_data(details[row['id']])
        require(output_items(runs, 'Synthetic output').get('result') == 'synthetic-state-only',
                'Scheduled execution returned unexpected output')
        emitted = timestamp(output_items(runs, 'Synthetic schedule').get('timestamp'))
        slot = math.floor(emitted / 5)
        require(slot not in slots, 'Duplicate scheduled emission in a five-second cadence slot')
        slots.add(slot)
    return sum(row['status'] == 'success' for row in rows)


def scheduler_snapshot(workflow):
    require(workflow.get('active') is True, 'Synthetic scheduler is not active')
    try:
        schedule = [n for n in workflow['nodes'] if n['type'] == 'n8n-nodes-base.scheduleTrigger']
        require(len(schedule) == 1, 'Expected one scheduler node')
        interval = schedule[0]['parameters']['rule']['interval']
        require(interval == [{'field': 'minutes', 'minutesInterval': 7}], 'Recurrence configuration changed')
        require(workflow['settings']['timezone'] == 'Asia/Kolkata', 'Scheduler timezone changed')
        state = workflow['staticData']['node:Synthetic schedule']
        rules, signatures = state['recurrenceRules'], state['recurrenceRuleSignatures']
        require(signatures == ['minutes:7'], 'Persistent recurrence signature missing or changed')
        require(isinstance(rules, list) and len(rules) == 1 and
                type(rules[0]) in (int, float) and math.isfinite(rules[0]) and rules[0] >= 12345,
                'Persistent scheduler last-run state missing or invalid')
        return copy.deepcopy({'interval': interval, 'timezone': workflow['settings']['timezone'],
                              'signatures': signatures, 'lastRun': rules[0]})
    except (KeyError, TypeError):
        raise Failure('Required persistent scheduler state/configuration absent') from None


def validate_restart(before, after):
    for key in ('interval', 'timezone', 'signatures'):
        require(before[key] == after[key], 'Restart changed recurrence configuration or signature')
    require(after['lastRun'] >= before['lastRun'], 'Restart lost or regressed persistent scheduler state')


def durable_job_snapshot(rows, workflow_id, native=False):
    require(isinstance(rows, list) and len(rows) == 1, 'Expected one persistent durable schedule job')
    row = rows[0]
    require(row.get('taskType') == 'workflow:schedule-trigger' and
            row.get('payload', {}).get('workflowId') == workflow_id,
            'Durable job does not belong to the synthetic scheduler')
    require(row.get('enabled') is True and row.get('orphanedAt') is None,
            'Durable synthetic schedule is disabled or quarantined')
    if native:
        require(row.get('kind') == 'interval' and row.get('intervalSeconds') == 420,
                'Seven-minute rule was not provisioned as a durable interval')
    else:
        require((row.get('kind') == 'interval' and row.get('intervalSeconds') == 5) or
                (row.get('kind') == 'cron' and row.get('cronExpression') == '*/5 * * * * *'),
                'Fast durable job has unexpected recurrence')
    require(row.get('id') is not None and row.get('nextRunAt') is not None,
            'Durable job identity or persistent clock missing')
    config_keys = ('id', 'kind', 'cronExpression', 'timezone', 'intervalSeconds',
                   'recurrenceUnit', 'recurrenceSize', 'taskType', 'payload')
    return {'configuration': {k: row.get(k) for k in config_keys},
            'nextRunAt': timestamp(row['nextRunAt'])}


def validate_durable_restart(before, after):
    require(before['configuration'] == after['configuration'],
            'Restart lost/recreated/changed the durable schedule job')
    require(after['nextRunAt'] >= before['nextRunAt'], 'Restart regressed the durable scheduler clock')


def durable_tasks_snapshot(rows):
    snapshot = {}
    slots = set()
    for row in rows:
        require(row.get('id') is not None and row.get('jobId') is not None,
                'Durable task identity missing')
        scheduled = timestamp(row.get('scheduledFor'))
        identity = (str(row['jobId']), scheduled)
        require(identity not in slots, 'Duplicate durable occurrence identity')
        slots.add(identity)
        require(row.get('status') not in {'failed', 'error', 'dead', 'cancelled', 'expired'} and
                not row.get('errorMessage') and row.get('attempts', 0) <= 1,
                'Durable scheduler task failed, expired or unexpectedly retried')
        snapshot[str(row['id'])] = identity
    return snapshot


def bounded_wait(probe, description, timeout=90, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + timeout
    while True:
        result = probe()
        if result:
            return result
        remaining = deadline - clock()
        require(remaining > 0, 'Timed out waiting for ' + description)
        sleep(min(2, remaining))


class Runner:
    def __init__(self, env):
        self.env = env
        self.base = ['docker', '--config', env['DOCKER_CONFIG'], '--host', ENDPOINT]
        self.prefix = ['compose', '--env-file', '/dev/null', '-p', PROJECT,
                       '-f', str(HERE / 'compose.json'), '--profile', 'integration']
        self.password = secrets.token_urlsafe(24) + 'aA1!'
        self.ids = {}
        self.details = {}

    def command(self, args, data=None, timeout=45):
        try:
            result = subprocess.run(self.base + args, input=data, text=True, capture_output=True,
                                    env=self.env, cwd=ROOT, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            raise Failure('Docker command exceeded its bounded timeout') from None
        require(result.returncode == 0, 'Docker operation failed; raw output suppressed to protect credentials')
        return result.stdout

    def compose(self, *args, **kwargs):
        return self.command(self.prefix + list(args), **kwargs)

    def json_command(self, args):
        return json.loads(self.command(args))

    def sql(self, query, database='dincharya_n8n_test'):
        require(database in {'dincharya_n8n_test', 'dincharya_app_test'}, 'Non-test database rejected')
        return self.compose('exec', '-T', 'postgres-test', 'psql', '-X', '-v', 'ON_ERROR_STOP=1',
                            '-U', 'synthetic_test', '-d', database, '-At', '-c', query).strip()

    def api(self, action, **values):
        script = (HERE / 'api-client.js').read_text()
        # Source on argv, synthetic password only on stdin. Never log raw output.
        response = self.compose('exec', '-T', 'n8n-test', 'node', '-e', script,
                                data=json.dumps({'action': action, 'password': self.password, **values}))
        return json.loads(response)

    def workflow(self, key='scheduler-state'):
        wid = self.ids[key]
        require(re.fullmatch(r'[A-Za-z0-9_-]+', wid) is not None, 'Unexpected synthetic workflow ID')
        result = self.sql('SELECT row_to_json(w) FROM workflow_entity w WHERE id=' + "'" + wid + "'")
        return json.loads(result)

    def executions(self, key='scheduler-state'):
        wid = self.ids[key]
        require(re.fullmatch(r'[A-Za-z0-9_-]+', wid) is not None, 'Unexpected synthetic workflow ID')
        rows = json.loads(self.sql('SELECT coalesce(json_agg(e),\'[]\'::json) FROM '
            '(SELECT id::text, status, mode, "startedAt" FROM execution_entity WHERE "workflowId"=' +
            "'" + wid + "' ORDER BY id) e"))
        for row in rows:
            if row['status'] == 'success' and row['id'] not in self.details:
                self.details[row['id']] = self.api('execution', id=row['id'])
        count = validate_emissions(rows, self.details)
        return rows, count

    def inspect(self, cid):
        return self.json_command(['inspect', cid])[0]

    def isolation(self):
        ids = self.compose('ps', '-q').split()
        require(len(ids) == 3, 'Expected exactly three healthy test containers')
        config = json.loads((HERE / 'compose.json').read_text())
        for cid in ids:
            c = self.inspect(cid)
            service = c['Config']['Labels'].get('com.docker.compose.service')
            require(service in SERVICES and c['Config']['Labels'].get('com.docker.compose.project') == PROJECT,
                    'Unexpected container project/service')
            require(c['Image'] == IMAGES[service], 'Unexpected runtime image')
            require(set(c['NetworkSettings']['Networks']) == {NETWORK}, 'Unexpected container network')
            host = c['HostConfig']
            require(not host['PortBindings'] and not host['Privileged'] and host['ReadonlyRootfs'],
                    'Unsafe container ports/privileges/filesystem')
            expected = {(str((HERE / m['source']).resolve()), m['target'])
                        for m in config['services'][service].get('volumes', [])}
            actual = set()
            for m in c['Mounts']:
                if m['Type'] == 'tmpfs':
                    continue
                require(m['Type'] == 'bind' and not m['RW'], 'Unsafe persistent/writable mount')
                actual.add((m['Source'], m['Destination']))
            require(actual == expected, 'Unexpected fixture mount')
        net = self.json_command(['network', 'inspect', NETWORK])[0]
        require(net['Internal'] and set(net['Containers']) == set(ids), 'Test network is not isolated')

    def import_workflows(self):
        saved = self.api('bootstrap')
        self.ids = saved['ids']
        fixture = json.loads((HERE / 'fixtures/scheduler-state.json').read_text())
        require(saved['importedState'] is None and self.workflow().get('staticData') is None,
                'Pinned workflow-create API state behavior changed')
        print('Create API drops native state; testing native CLI import preservation', flush=True)
        self.compose('exec', '-T', '-e', 'N8N_LOG_LEVEL=info',
                     '-e', 'N8N_RUNNERS_BROKER_PORT=5680', 'n8n-test', 'n8n', 'import:workflow',
                     '--input=/tmp/synthetic-scheduler-import.json', timeout=60)
        require(self.workflow().get('staticData') == fixture['staticData'],
                'Native CLI import did not preserve synthetic scheduler state')
        require(self.workflow('native-gate').get('staticData') == saved['nativeState'],
                'Native CLI import did not preserve synthetic minutes gate state')

    def fast_configuration(self):
        workflow = self.workflow()
        require(workflow.get('active') is True, 'Fast scheduler lost activation')
        rules = [n['parameters']['rule']['interval'] for n in workflow['nodes']
                 if n['type'] == 'n8n-nodes-base.scheduleTrigger']
        expected = [[{'field': 'seconds', 'secondsInterval': 5}]]
        require(rules == expected and workflow['settings'].get('timezone') == 'Asia/Kolkata',
                'Fast recurrence configuration or timezone changed')
        return {'rules': rules, 'timezone': workflow['settings']['timezone']}

    def jobs(self, key='scheduler-state'):
        wid = self.ids[key]
        require(re.fullmatch(r'[A-Za-z0-9_-]+', wid) is not None, 'Unexpected synthetic workflow ID')
        query = "SELECT coalesce(json_agg(j),'[]'::json) FROM scheduled_job j WHERE payload->>'workflowId'='" + wid + "'"
        return json.loads(self.sql(query))

    def tasks(self, job_ids):
        require(all(re.fullmatch(r'[A-Za-z0-9_-]+', str(i)) for i in job_ids), 'Invalid synthetic durable job ID')
        ids = ','.join("'" + str(i) + "'" for i in job_ids)
        return json.loads(self.sql("SELECT coalesce(json_agg(t),'[]'::json) FROM scheduled_task t WHERE \"jobId\" IN (" + ids + ')'))

    def tests(self):
        require(self.sql('SELECT count(*) FROM synthetic_events', 'dincharya_app_test') == '1',
                'Synthetic application initialization failed')
        self.import_workflows()
        manual_id = self.ids['manual-smoke']
        raw = self.compose('exec', '-T', '-e', 'N8N_LOG_LEVEL=info',
                           '-e', 'N8N_RUNNERS_BROKER_PORT=5680',
                           'n8n-test', 'n8n', 'execute', '--id', manual_id, '--rawOutput')
        validate_manual(parse_cli_result(raw))
        print('Manual synthetic-pass verified', flush=True)
        self.api('activate', id=self.ids['scheduler-state'])
        self.api('activate-native', id=self.ids['native-gate'])
        bounded_wait(lambda: self.executions()[1] >= 5, 'five successful scheduled outputs')
        print('Five successful fast scheduled outputs verified', flush=True)
        # The pinned default durable scheduler intercepts these rules. Legacy
        # recurrence arrays remain imported state, not its active timer clock.
        before = scheduler_snapshot(self.workflow('native-gate'))
        fast_config = self.fast_configuration()
        before_jobs = {key: durable_job_snapshot(self.jobs(key), self.ids[key], key == 'native-gate')
                       for key in ('scheduler-state', 'native-gate')}
        job_ids = [value['configuration']['id'] for value in before_jobs.values()]
        before_tasks = durable_tasks_snapshot(self.tasks(job_ids))
        require(bool(before_tasks), 'No durable occurrences persisted before restart')
        print('Persistent durable jobs/occurrences and preserved legacy arrays verified', flush=True)
        old_ids = {row['id'] for row in self.executions()[0]}
        pg_id = self.compose('ps', '-q', 'postgres-test').strip()
        pg_started = self.inspect(pg_id)['State']['StartedAt']
        self.compose('restart', 'n8n-test', timeout=60)
        cid = self.compose('ps', '-q', 'n8n-test').strip()
        bounded_wait(lambda: self.inspect(cid)['State'].get('Health', {}).get('Status') == 'healthy',
                     'n8n restart readiness')
        resumed_after = time.time()
        validate_restart(before, scheduler_snapshot(self.workflow('native-gate')))
        def resumed():
            rows, _ = self.executions()
            return sum(r['status'] == 'success' and r['id'] not in old_ids and
                       timestamp(r['startedAt']) >= resumed_after for r in rows) >= 3
        bounded_wait(resumed, 'three successful emissions after restart')
        print('Three successful fast emissions after restart readiness verified', flush=True)
        validate_restart(before, scheduler_snapshot(self.workflow('native-gate')))
        require(self.compose('ps', '-q', 'postgres-test').strip() == pg_id and
                self.inspect(pg_id)['State']['StartedAt'] == pg_started, 'PostgreSQL restarted unexpectedly')
        require(self.fast_configuration() == fast_config, 'Restart changed fast recurrence configuration')
        after_jobs = {key: durable_job_snapshot(self.jobs(key), self.ids[key], key == 'native-gate')
                      for key in before_jobs}
        for key in before_jobs:
            validate_durable_restart(before_jobs[key], after_jobs[key])
        after_tasks = durable_tasks_snapshot(self.tasks(job_ids))
        require(all(after_tasks.get(key) == value for key, value in before_tasks.items()),
                'Restart lost or changed persisted durable occurrence identities')
        # Observe a further bounded window for duplicate/premature native emissions.
        observe_until = time.monotonic() + 20
        while time.monotonic() < observe_until:
            self.executions()
            self.executions('native-gate')
            durable_tasks_snapshot(self.tasks(job_ids))
            time.sleep(min(2, max(0, observe_until - time.monotonic())))
        validate_restart(before, scheduler_snapshot(self.workflow('native-gate')))
        self.api('deactivate', id=self.ids['scheduler-state'])
        self.api('deactivate', id=self.ids['native-gate'])
        # All executions must settle successfully; errors/in-flight hangs fail closed.
        bounded_wait(lambda: all(r['status'] == 'success' for key in ('scheduler-state', 'native-gate')
                                 for r in self.executions(key)[0]),
                     'all scheduled executions to succeed', timeout=20)
        print('Observed cadence slots unique; persistent configuration/state and restart recovery verified', flush=True)


def execute(expected_id):
    validate_configuration(json.loads((HERE / 'compose.json').read_text()))
    with tempfile.TemporaryDirectory(prefix='dincharya-m2c-docker-') as directory:
        env = client_environment(os.environ, directory)
        Path(directory, 'config.json').write_text('{}\n')
        os.chmod(Path(directory, 'config.json'), 0o600)
        require(stat.S_ISSOCK(os.stat('/var/run/docker.sock').st_mode), 'Expected local Docker socket absent')
        runner = Runner(env)
        validate_daemon(runner.json_command(['info', '--format', '{{json .}}']), expected_id)
        # Preflight does not read resolved production environments or credentials.
        require(not runner.command(['ps', '-aq', '--filter', 'label=com.docker.compose.project=' + PROJECT]).strip(),
                'Test project already has containers; refusing ownership/cleanup')
        require(NETWORK not in runner.command(['network', 'ls', '--format', '{{.Name}}']).split(),
                'Test network already exists; refusing ownership/cleanup')
        before = set(runner.command(['ps', '-q']).split())
        for image in set(IMAGES.values()):
            info = runner.json_command(['image', 'inspect', image])[0]
            require(info['Id'] == image, 'Pinned local image missing')
            if image == IMAGES['n8n-test']:
                require(info['Config']['Labels'].get('org.opencontainers.image.version') == '2.47.3',
                        'Pinned n8n image version mismatch')
        env.update(DINCHARYA_TEST_POSTGRES_IMAGE=IMAGES['postgres-test'],
                   DINCHARYA_TEST_N8N_IMAGE=IMAGES['n8n-test'],
                   DINCHARYA_TEST_DB_PASSWORD=secrets.token_urlsafe(32),
                   DINCHARYA_TEST_ENCRYPTION_KEY=secrets.token_hex(32))
        try:
            print('Starting pinned disposable synthetic stack', flush=True)
            runner.compose('up', '-d', '--wait', '--wait-timeout', '180', timeout=200)
            runner.isolation()
            print('Three healthy services; runtime isolation verified', flush=True)
            runner.tests()
        finally:
            try:
                print('Removing only the disposable integration project', flush=True)
                runner.compose('down', '--timeout', '20', timeout=60)
                require(not runner.command(['ps', '-aq', '--filter',
                        'label=com.docker.compose.project=' + PROJECT]).strip(), 'Test containers remain after cleanup')
                require(NETWORK not in runner.command(['network', 'ls', '--format', '{{.Name}}']).split(),
                        'Test network remains after cleanup')
                require(set(runner.command(['ps', '-q']).split()) == before,
                        'Original running container inventory changed during test')
                print('Teardown verified; original running container IDs unchanged', flush=True)
            finally:
                runner.password = ''
                env.clear()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-approved', action='store_true')
    parser.add_argument('--expected-daemon-id', required=True)
    args = parser.parse_args()
    require(args.execute_approved, 'Execution requires explicit operator approval')
    def interrupt(signum, frame):
        raise Failure('Interrupted; attempting project cleanup')
    signal.signal(signal.SIGTERM, interrupt)
    try:
        execute(args.expected_daemon_id)
    except (Failure, OSError, ValueError, KeyError, TypeError, KeyboardInterrupt):
        # Detailed Failure messages are safe; never echo arbitrary exception/response contents.
        import sys
        error = sys.exc_info()[1]
        print(str(error) if isinstance(error, Failure) else 'Integration failed; unexpected runtime contract or interruption',
              file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
