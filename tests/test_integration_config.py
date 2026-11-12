import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
INTEGRATION=ROOT/'tests/integration'


class IntegrationConfigTests(unittest.TestCase):
    def setUp(self):self.config=json.loads((INTEGRATION/'compose.json').read_text())

    def test_only_separate_synthetic_services_and_internal_network(self):
        self.assertEqual(set(self.config['services']),{'postgres-test','n8n-test','mock-services'})
        self.assertEqual(self.config['networks'],{'synthetic-only':{'internal':True}})
        self.assertNotIn('volumes',self.config)
        for service in self.config['services'].values():
            self.assertEqual(service['networks'],['synthetic-only'])
            self.assertEqual(service['profiles'],['integration'])
            for forbidden in ('ports','container_name','network_mode','env_file','privileged','pid','ipc','extends'):
                self.assertNotIn(forbidden,service)

    def test_no_pulls_autorestarts_or_mutable_image_defaults(self):
        for service in self.config['services'].values():
            self.assertEqual(service['pull_policy'],'never')
            self.assertEqual(service['restart'],'no')
            self.assertRegex(service['image'],r'^\$\{DINCHARYA_TEST_(?:POSTGRES|N8N)_IMAGE:\?')
            self.assertTrue(service['read_only'])
            self.assertEqual(service['security_opt'],['no-new-privileges:true'])

    def test_only_readonly_test_fixture_bind_mounts(self):
        expected={'./postgres-init.sql','./mock-services.js','./fixtures/manual-smoke.json','./fixtures/scheduler-state.json'}
        actual=set()
        for service in self.config['services'].values():
            for mount in service.get('volumes',[]):
                self.assertEqual(mount['type'],'bind');self.assertTrue(mount['read_only'])
                self.assertNotIn('..',Path(mount['source']).parts)
                self.assertTrue((INTEGRATION/mount['source']).exists())
                self.assertTrue((INTEGRATION/mount['source']).is_file())
                actual.add(mount['source'])
        self.assertEqual(actual,expected)

    def test_database_targets_and_credentials_are_test_only(self):
        pg=self.config['services']['postgres-test']['environment']
        env=self.config['services']['n8n-test']['environment']
        self.assertEqual(pg['POSTGRES_DB'],'dincharya_n8n_test')
        self.assertEqual(env['DB_POSTGRESDB_HOST'],'postgres-test')
        self.assertEqual(env['DB_POSTGRESDB_DATABASE'],pg['POSTGRES_DB'])
        for value in (pg['POSTGRES_PASSWORD'],env['DB_POSTGRESDB_PASSWORD'],env['N8N_ENCRYPTION_KEY']):
            self.assertRegex(value,r'^\$\{DINCHARYA_TEST_.*:\?')
        self.assertNotIn('POSTGRES_HOST_AUTH_METHOD',pg)

    def test_runtime_data_is_ephemeral_and_no_production_hosts(self):
        services=self.config['services']
        self.assertTrue(any('/var/lib/postgresql/data' in path for path in services['postgres-test']['tmpfs']))
        self.assertTrue(any('/home/node/.n8n' in path for path in services['n8n-test']['tmpfs']))
        text=json.dumps(self.config)
        for forbidden in ('api.telegram.org','host.docker.internal','docker.sock','postgres_data','n8n_data','dincharya_app"'):
            self.assertNotIn(forbidden,text)
        self.assertEqual(services['mock-services']['entrypoint'],['node','/opt/synthetic/mock-services.js'])
        self.assertEqual(services['mock-services']['command'],[])

    def test_synthetic_workflows_inactive_without_code_or_external_calls(self):
        for path in (INTEGRATION/'fixtures').glob('*.json'):
            fixture=json.loads(path.read_text())
            self.assertIs(fixture['active'],False)
            self.assertNotIn('id',fixture)
            for node in fixture['nodes']:
                self.assertIn(node['type'],{'n8n-nodes-base.manualTrigger','n8n-nodes-base.scheduleTrigger','n8n-nodes-base.set'})
                self.assertNotIn('credentials',node)
                self.assertNotIn('jsCode',node['parameters'])

    def test_synthetic_state_has_no_production_identifiers(self):
        fixture=json.loads((INTEGRATION/'fixtures/scheduler-state.json').read_text())
        self.assertEqual(set(fixture['staticData']),{'node:Synthetic schedule'})
        state=fixture['staticData']['node:Synthetic schedule']
        self.assertEqual(set(state),{'recurrenceRules','recurrenceRuleSignatures'})
        self.assertTrue(all(node['id'].startswith('synthetic-') for node in fixture['nodes']))

    def test_mock_never_logs_payload_or_calls_external_services(self):
        text=(INTEGRATION/'mock-services.js').read_text()
        for forbidden in ('console.','fetch(','https://','child_process','eval('):
            self.assertNotIn(forbidden,text)
        self.assertIn('16384',text)
        self.assertIn("request.url === '/health'",text)
        self.assertIn("request.url === '/telegram/sendMessage'",text)
        self.assertIn("request.url === '/ollama/api/chat'",text)


if __name__=='__main__':unittest.main()
