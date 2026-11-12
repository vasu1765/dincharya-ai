import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import source_sync as sync
import version_evidence as evidence


class VersionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {'id':'synthetic-workflow','versionId':'synthetic-current',
                         'activeVersionId':'synthetic-published','active':True,
                         'nodes':[{'synthetic':1}], 'connections':{},'settings':{},
                         'staticData':{'node:Synthetic scheduler':{'recurrenceRules':[None],'recurrenceRuleSignatures':[None]}}}
        self.history = [{'workflow_id':'synthetic-workflow','version_id':'synthetic-published',
                         'content':{'nodes':[{'synthetic':2}],'connections':{}}}]
        self.references = [{'workflow_id':'synthetic-workflow','version_id':'synthetic-published',
                            'role':'current','source_table':'workflow_published_version'}]

    def resolve(self):
        return evidence.resolve_versions(self.snapshot,self.history,self.references,'a'*64,'b'*64)

    def test_distinct_published_body_compared_without_substitution(self):
        result=self.resolve()
        self.assertTrue(result['published_body_located'])
        self.assertTrue(result['current_published_differ_on_compared_fields'])
        self.assertFalse(result['full_content_comparison_complete'])
        self.assertNotEqual(result['published_reference_id'],result['current_version_id'])
        self.assertFalse(result['executing_version_established'])

    def test_missing_body_is_unknown_not_equal(self):
        self.history=[]
        result=self.resolve()
        self.assertEqual(result['body_status'],'missing_referenced_body')
        self.assertIsNone(result['current_published_differ_on_compared_fields'])

    def test_no_reference_does_not_select_latest_historical_event(self):
        self.snapshot['activeVersionId']=None
        self.references[0]['role']='historical'
        result=self.resolve()
        self.assertIsNone(result['published_reference_id'])
        self.assertEqual(result['body_status'],'publication_reference_unavailable')

    def test_conflicting_current_references_reject(self):
        other=dict(self.references[0],version_id='other-synthetic-version')
        self.references.append(other)
        with self.assertRaises(sync.Rejected):self.resolve()

    def test_snapshot_reference_conflict_rejects(self):
        self.references[0]['version_id']='other-synthetic-version'
        with self.assertRaises(sync.Rejected):self.resolve()

    def test_duplicate_history_conflicts_reject(self):
        self.history.append(dict(self.history[0],content={'nodes':[],'connections':{}}))
        with self.assertRaises(sync.Rejected):self.resolve()

    def test_identical_history_rows_count_once(self):
        self.history.append(copy.deepcopy(self.history[0]))
        self.assertEqual(self.resolve()['relevant_unique_history_count'],1)

    def test_equal_fields_do_not_establish_missing_settings_or_execution(self):
        self.history[0]['content']['nodes']=copy.deepcopy(self.snapshot['nodes'])
        result=self.resolve()
        self.assertFalse(result['current_published_differ_on_compared_fields'])
        self.assertFalse(result['full_content_comparison_complete'])
        self.assertFalse(result['production_schema_mapping_verified'])
        self.assertFalse(result['executing_version_established'])

    def test_state_and_source_unchanged(self):
        before=copy.deepcopy((self.snapshot,self.history,self.references))
        result=self.resolve()
        self.assertEqual(before,(self.snapshot,self.history,self.references))
        self.assertFalse(result['state_treatment_approved'])

    def test_provenance_reconstruction_rejects_rehashed_claim(self):
        raw=sync.encoded(self.snapshot)
        normalized=sync.encoded({'histories':self.history,'references':self.references,'archive_sha256':'a'*64})
        files,result=evidence.version_report_payload(raw,normalized)
        self.assertEqual(evidence.validate_version_report(files),result)
        altered=sync.decode_json(files['resolution.private.json']);altered['executing_version_established']=True
        files['resolution.private.json']=sync.encoded(altered)
        manifest=sync.decode_json(files['manifest.json']);manifest['files_sha256']['resolution.private.json']=sync.digest(files['resolution.private.json'])
        files['manifest.json']=sync.encoded(manifest)
        with self.assertRaises(sync.Rejected):evidence.validate_version_report(files)

    def test_invalid_hash_and_incomplete_body_fail_closed(self):
        with self.assertRaises(sync.Rejected):evidence.resolve_versions(self.snapshot,[],[],'invalid','b'*64)
        del self.history[0]['content']['connections']
        with self.assertRaises(sync.Rejected):self.resolve()

    def toc(self):
        rows=[]
        for i,table in enumerate(sorted(evidence.AUTHORIZED_TABLES)):
            rows.extend([f'{i*2+1}; 1259 1 TABLE public {table} synthetic',
                         f'{i*2+2}; 0 1 TABLE DATA public {table} synthetic'])
        rows.append('99; 0 5 TABLE DATA public credentials_entity synthetic')
        return '\n'.join(rows)

    def test_toc_plan_selects_only_six_exact_entries(self):
        plan=evidence.plan_authorized_toc(self.toc())
        self.assertEqual(len(plan),6)
        self.assertEqual({entry['table'] for entry in plan},evidence.AUTHORIZED_TABLES)
        self.assertNotIn(99,{entry['entry_id'] for entry in plan})

    def test_ambiguous_schema_and_missing_entries_fail_closed(self):
        with self.assertRaises(sync.Rejected):evidence.plan_authorized_toc(self.toc().replace('TABLE public','TABLE other',1))
        with self.assertRaises(sync.Rejected):evidence.plan_authorized_toc('\n'.join(self.toc().splitlines()[1:]))

    def test_unapproved_reference_source_rejected(self):
        self.references[0]['source_table']='execution_entity'
        with self.assertRaises(sync.Rejected):self.resolve()

    def test_contradictory_active_metadata_rejected(self):
        self.snapshot['active']=False
        with self.assertRaises(sync.Rejected):self.resolve()
        self.snapshot['active']='yes'
        with self.assertRaises(sync.Rejected):self.resolve()

    def test_numeric_boolean_difference_is_not_hidden(self):
        self.snapshot['nodes']=[{'synthetic':True}]
        self.history[0]['content']['nodes']=[{'synthetic':1}]
        self.assertTrue(self.resolve()['differences_by_field']['nodes'])

    def test_json_object_key_order_is_not_a_workflow_change(self):
        self.snapshot['nodes']=[{'id':'synthetic-node','parameters':{'a':1,'b':2}}]
        self.history[0]['content']['nodes']=[{'parameters':{'b':2,'a':1},'id':'synthetic-node'}]
        self.assertFalse(self.resolve()['differences_by_field']['nodes'])

    def test_array_order_and_code_text_still_count_as_changes(self):
        self.snapshot['nodes']=[{'id':'a'},{'id':'b'}]
        self.history[0]['content']['nodes']=[{'id':'b'},{'id':'a'}]
        self.assertTrue(self.resolve()['differences_by_field']['nodes'])
        self.snapshot['nodes']=[{'jsCode':'return 1;'}]
        self.history[0]['content']['nodes']=[{'jsCode':'return  1;'}]
        self.assertTrue(self.resolve()['differences_by_field']['nodes'])


if __name__=='__main__':unittest.main()
