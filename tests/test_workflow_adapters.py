import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('adapter_sync', ROOT / 'scripts/source_sync.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class WorkflowAdapterTests(unittest.TestCase):
    def setUp(self):
        self.records = json.loads((ROOT / 'tests/fixtures/observed-structures.synthetic.json').read_text())
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / 'snapshot.json'
        self.report = self.root / 'report.json'

    def convert(self):
        return sync.convert_workflows(sync.encoded(self.records), 'raw', 'unknown')

    def prepare(self):
        raw = sync.encoded(self.records)
        self.input.write_bytes(raw)
        self.report.write_bytes(sync.encoded({'inputs':[{'source_path':str(self.input), 'checksum_verified':True,'sha256':sync.digest(raw)}]}))
        return sync.prepare_workflow_snapshot(self.input, self.report, self.root / 'candidate', self.root)

    def test_all_versioned_data_adapters_preserve_parameters_and_edges(self):
        candidate, provenance = self.convert()
        self.assertEqual(candidate[0]['connections'], self.records[0]['connections'])
        self.assertEqual(candidate[0]['settings'], self.records[0]['settings'])
        self.assertEqual(provenance[0]['original_record'], self.records[0])
        for original, converted in zip(self.records[0]['nodes'],candidate[0]['nodes']):
            self.assertEqual(original['parameters'],converted['parameters'])
            self.assertNotIn('credentials',converted)
            self.assertEqual(original['id'],converted['id'])
        self.assertEqual(candidate[0]['nodes'][6]['webhookId'],'synthetic-webhook-binding')

    def test_database_metadata_not_silently_lost(self):
        candidate, provenance = self.convert()
        for key in ('nodeGroups','sourceWorkflowId','meta','versionId','activeVersionId'):
            self.assertNotIn(key,candidate[0])
            self.assertEqual(provenance[0]['original_record'][key],self.records[0][key])

    def test_unknown_fields_rejected_at_each_level(self):
        for target in (self.records[0],self.records[0]['meta'],self.records[0]['settings'],self.records[0]['nodes'][0],self.records[0]['nodes'][1]['parameters']['options']):
            target['unknownField']='synthetic'
            with self.subTest(target_type=type(target)), self.assertRaises(sync.Rejected):
                self.convert()
            del target['unknownField']

    def test_unreviewed_runtime_state_and_code_stay_blocked(self):
        self.records[0]['staticData']={'synthetic':{'state':1}}
        with self.assertRaisesRegex(sync.Rejected,'RUNTIME_STATE_REQUIRES_REVIEW'):
            self.convert()
        self.records[0]['staticData']=None
        self.records[0]['nodes'][0].update(type='n8n-nodes-base.code',typeVersion=2,parameters={'jsCode':'return []; // synthetic, never run'})
        with self.assertRaisesRegex(sync.Rejected,'EXECUTABLE_NODE_REQUIRES_REVIEW'):
            self.convert()

    def test_unknown_version_rejected_for_every_adapter(self):
        for node in self.records[0]['nodes']:
            old=node['typeVersion'];node['typeVersion']=999
            with self.subTest(node_type=node['type']),self.assertRaises(sync.Rejected):self.convert()
            node['typeVersion']=old

    def test_secret_checks_still_apply_to_query_and_prompt(self):
        for node_index,field in ((1,'query'),(4,'text')):
            original=self.records[0]['nodes'][node_index]['parameters'][field]
            self.records[0]['nodes'][node_index]['parameters'][field]='pass'+'word=synthetic-opaque'
            with self.assertRaises(sync.Rejected):self.convert()
            self.records[0]['nodes'][node_index]['parameters'][field]=original

    def test_credential_values_are_never_accepted(self):
        self.records[0]['nodes'][1]['credentials']['postgres']['pass'+'word']='synthetic'
        with self.assertRaises(sync.Rejected):self.convert()

    def test_bad_ai_edges_and_branch_overflow_rejected(self):
        connections=self.records[0]['connections']
        connections['Node5']['ai_languageModel'][0][0]['node']='Node1'
        with self.assertRaises(sync.Rejected):self.convert()
        connections['Node5']['ai_languageModel'][0][0]['node']='Node4'
        connections['Node8']['main'].append([])
        with self.assertRaises(sync.Rejected):self.convert()

    def test_publication_conflict_rejected_not_inferred(self):
        self.records[0].update(active=True,activeVersionId='different-published-version')
        with self.assertRaises(sync.Rejected):sync.convert_workflows(sync.encoded(self.records),'editor','published')
        candidate, provenance=self.convert()
        self.assertFalse(provenance[0]['state_verified'])
        self.assertEqual(provenance[0]['declared_state'],'unknown')
        self.assertFalse(candidate[0]['active'])

    def test_partial_bundle_preserves_rejected_originals(self):
        rejected=copy.deepcopy(self.records[0]);rejected['id']='synthetic-rejected';rejected['staticData']={'synthetic':1}
        self.records.append(rejected)
        result=self.prepare()
        self.assertEqual((result['converted_count'],result['rejected_count']),(1,1))
        self.assertFalse(result['promotion_approved'])
        self.assertFalse(result['human_review_attested'])
        self.assertEqual(sync.validate_workflow_snapshot(self.root/'candidate',self.root),result)
        stored=json.loads((self.root/'candidate/workflow-input.private.json').read_text())
        self.assertEqual(stored,self.records)
        for path in (self.root/'candidate').iterdir():self.assertEqual(path.stat().st_mode&0o777,0o600)

    def test_integrity_mismatch_prevents_output(self):
        self.input.write_bytes(sync.encoded(self.records))
        self.report.write_bytes(sync.encoded({'inputs':[]}))
        with self.assertRaises(sync.Rejected):sync.prepare_workflow_snapshot(self.input,self.report,self.root/'candidate',self.root)
        self.assertFalse((self.root/'candidate').exists())

    def test_snapshot_tampering_and_extra_manifest_flag_rejected(self):
        self.prepare()
        path=self.root/'candidate/manifest.json'
        manifest=json.loads(path.read_text());manifest['promotion_approved']=True;path.write_bytes(sync.encoded(manifest))
        with self.assertRaises(sync.Rejected):sync.validate_workflow_snapshot(self.root/'candidate',self.root)

    def test_partial_write_does_not_write_review_marker(self):
        real=sync.write_file
        def failure(fd,name,content):
            if name=='manifest.json':raise OSError('synthetic failure')
            return real(fd,name,content)
        with patch.object(sync,'write_file',side_effect=failure),self.assertRaises(OSError):self.prepare()
        self.assertFalse((self.root/'candidate/REVIEW_ONLY').exists())

    def test_unknown_nested_rule_rejected(self):
        self.records[0]['nodes'][9]['parameters']['rules']['values'][0]['conditions']['options']['unknown']=True
        with self.assertRaises(sync.Rejected):self.convert()


if __name__=='__main__':unittest.main()
