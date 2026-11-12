import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import source_sync as sync
import extracted_workflows as extracted
spec=importlib.util.spec_from_file_location('extracted_analysis',ROOT/'scripts/analyze-extracted-workflows.py')
analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)


def copy_field(value):
    if value is None:return r'\N'
    return str(value).replace('\\','\\\\').replace('\t',r'\t').replace('\n',r'\n').replace('\r',r'\r')


class ExtractedWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.snapshot=json.loads((ROOT/'tests/fixtures/workflow.raw.json').read_text())
        w=self.snapshot[0]
        w.update(active=True,versionId='synthetic-current',activeVersionId='synthetic-published')
        self.nodes=copy.deepcopy(w['nodes']);self.nodes[1]['parameters']['value']='Synthetic historical text\nनमस्ते'
        self.tables={
          'workflow_history':[{'versionId':'synthetic-published','workflowId':w['id'],'authors':'Synthetic author',
           'createdAt':'2000-01-01','updatedAt':'2000-01-01','nodes':sync.encoded(self.nodes).decode(),
           'connections':sync.encoded(w['connections']).decode(),'name':'Synthetic historical workflow',
           'autosaved':'f','description':None,'nodeGroups':'[]'}],
          'workflow_publish_history':[{'id':'1','workflowId':w['id'],'versionId':'synthetic-published',
           'event':'activated','userId':'synthetic-user','createdAt':'2000-01-01'},
           {'id':'2','workflowId':w['id'],'versionId':None,'event':'deactivated','userId':None,'createdAt':'2000-01-02'}],
          'workflow_published_version':[{'workflowId':w['id'],'publishedVersionId':'synthetic-published',
           'createdAt':'2000-01-01','updatedAt':'2000-01-01'}]}

    def sql(self):
        parts=['-- synthetic pg_restore selected output\nSET statement_timeout = 0;\n']
        for table,columns in extracted.COLUMNS.items():
            parts.append('CREATE TABLE public.'+table+' (\n'+',\n'.join('"'+c+'" text' for c in columns)+'\n);\n')
        for table,columns in extracted.COLUMNS.items():
            parts.append('COPY public.'+table+' ('+', '.join('"'+c+'"' for c in columns)+') FROM stdin;\n')
            for row in self.tables[table]:parts.append('\t'.join(copy_field(row[c]) for c in columns)+'\n')
            parts.append('\\.\n')
        return ''.join(parts).encode()

    def analyze(self):return extracted.analyze_versions(sync.encoded(self.snapshot),self.sql(),'a'*64)

    def test_copy_decode_preserves_unicode_json_backslashes_and_newlines(self):
        result=extracted.parse_extraction(self.sql())
        self.assertEqual(result,self.tables)
        self.assertEqual(sync.decode_json(result['workflow_history'][0]['nodes']),self.nodes)
        self.assertEqual(extracted.decode_copy_field(r'\303\251'),'é')
        self.assertEqual(extracted.decode_copy_field(r'\x41'),'A')

    def test_copy_unknown_escapes_truncation_and_columns_fail_closed(self):
        for value in ('abc\\',r'\q',r'\xZZ'):
            with self.subTest(value=value),self.assertRaises(sync.Rejected):extracted.decode_copy_field(value)
        with self.assertRaises(sync.Rejected):extracted.parse_extraction(self.sql().replace(b'"authors", ',b''))
        with self.assertRaises(sync.Rejected):extracted.parse_extraction(self.sql()[:-3])

    def test_unapproved_definitions_and_copy_tables_rejected(self):
        for content in (self.sql()+b'CREATE TABLE public.execution_entity (id int);\n',
                        self.sql()+b'COPY public.credentials_entity (id) FROM stdin;\n1\n\\.\n'):
            with self.assertRaises(sync.Rejected):extracted.parse_extraction(content)

    def test_published_version_is_separate_and_differences_compare_available_fields(self):
        result=self.analyze();r=result['resolutions'][0]
        self.assertTrue(r['published_body_located'])
        self.assertTrue(r['differences_by_field']['nodes'])
        self.assertFalse(r['full_content_comparison_complete'])
        self.assertFalse(result['published_bodies'][0]['settings_available'])
        self.assertEqual(result['published_bodies'][0]['decoded_nodes'],self.nodes)
        self.assertNotEqual(result['published_bodies'][0]['decoded_nodes'],self.snapshot[0]['nodes'])

    def test_unversioned_activation_and_deactivation_preserved_not_substituted(self):
        self.tables['workflow_publish_history'][0]['versionId']=None
        result=self.analyze()
        self.assertEqual(len(result['unversioned_events']),2)
        self.assertTrue(result['resolutions'][0]['published_body_located'])
        self.assertEqual(result['tables'],self.tables)

    def test_missing_body_not_invented_from_current(self):
        self.tables['workflow_history']=[]
        result=self.analyze()
        self.assertFalse(result['resolutions'][0]['published_body_located'])
        self.assertEqual(result['published_bodies'],[])

    def test_unknown_event_and_extra_columns_rejected(self):
        self.tables['workflow_publish_history'][0]['event']='synthetic-unknown'
        with self.assertRaises(sync.Rejected):self.analyze()

    def test_snapshot_publication_conflict_rejects(self):
        self.tables['workflow_published_version'][0]['publishedVersionId']='synthetic-conflict'
        with self.assertRaises(sync.Rejected):self.analyze()

    def test_current_state_and_code_never_removed_to_create_candidate(self):
        self.snapshot[0]['staticData']={'global':{'synthetic':1}}
        before=copy.deepcopy(self.snapshot)
        result=self.analyze()
        self.assertEqual(result['current_candidates'],[])
        self.assertEqual(result['rejections'][0]['category'],'RUNTIME_STATE_REQUIRES_REVIEW')
        self.assertEqual(self.snapshot,before)

    def test_private_analysis_reconstruction_and_rehashed_tampering(self):
        proof={'archive_sha256':'a'*64,'verified_checksums':{}}
        raw=sync.encoded(self.snapshot)
        files,result=analysis.analysis_files(raw,self.sql(),'a'*64,proof)
        self.assertEqual(files['current-snapshot.original.private.json'],raw)
        self.assertEqual(analysis.validate_analysis_files(files),result)
        manifest=sync.decode_json(files['manifest.json']);manifest['source_promotion_approved']=True
        files['manifest.json']=sync.encoded(manifest)
        with self.assertRaises(sync.Rejected):analysis.validate_analysis_files(files)

    def test_missing_historical_event_body_does_not_override_current_reference(self):
        event=dict(self.tables['workflow_publish_history'][0],id='3',versionId='synthetic-missing-eventbody')
        self.tables['workflow_publish_history'].append(event)
        result=self.analyze()
        self.assertTrue(result['resolutions'][0]['published_body_located'])
        self.assertEqual(len(result['event_references']),2)
        self.assertEqual(sum(not r['body_available'] for r in result['event_references']),1)

    def test_null_history_groups_are_preserved_not_invented(self):
        self.tables['workflow_history'][0]['nodeGroups']=None
        result=self.analyze()
        self.assertIsNone(result['published_bodies'][0]['original_history_record']['nodeGroups'])

    def test_other_sql_side_effect_statements_are_rejected(self):
        for suffix in (b'DO $$ BEGIN END; $$;\n',b'CREATE FUNCTION synthetic() RETURNS int LANGUAGE SQL AS $$ SELECT 1 $$;\n',b'\\! echo synthetic\n'):
            with self.subTest(suffix=suffix),self.assertRaises(sync.Rejected):extracted.parse_extraction(self.sql()+suffix)

    def test_position_only_difference_does_not_imply_code_or_connection_change(self):
        nodes=copy.deepcopy(self.snapshot[0]['nodes']);nodes[0]['position']=[999,100]
        self.tables['workflow_history'][0]['nodes']=sync.encoded(nodes).decode()
        result=self.analyze()['resolutions'][0]
        self.assertEqual(result['node_definition_diff']['changed_node_field_counts'],{'position':1})
        self.assertEqual(result['node_definition_diff']['changed_code_body_count'],0)
        self.assertFalse(result['differences_by_field']['connections'])
        self.assertFalse(result['node_definition_diff']['runtime_behavior_equivalence_established'])


if __name__=='__main__':unittest.main()
