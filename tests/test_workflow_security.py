import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import source_sync as sync
import workflow_security as review


class WorkflowSecurityTests(unittest.TestCase):
    def setUp(self):
        self.code = {'id': 'synthetic-code', 'name': 'Synthetic transform',
                     'type': 'n8n-nodes-base.code', 'typeVersion': 2, 'position': [0, 0],
                     'parameters': {'jsCode': '// synthetic\r\nreturn $input.all(); // नमस्ते\r\n'}}
        self.workflow = {'id': 'synthetic-workflow', 'name': 'Synthetic',
                         'active': True, 'versionId': 'synthetic-current',
                         'activeVersionId': 'synthetic-published', 'nodes': [self.code],
                         'connections': {}, 'settings': {}, 'staticData': None}

    def test_code_structure_and_utf8_bytes_preserved(self):
        node = review.preserve_code_v2_for_review(self.code)
        self.assertEqual(node, self.code)
        self.assertIsNot(node, self.code)
        self.assertEqual(node['parameters']['jsCode'].encode(), self.code['parameters']['jsCode'].encode())
        result = review.inspect_code_v2(node)
        self.assertEqual(result['code_utf8_sha256'], sync.digest(self.code['parameters']['jsCode'].encode()))
        self.assertFalse(result['execution_performed'])
        self.assertFalse(result['conversion_approved'])

    def test_wrong_version_or_unknown_code_fields_rejected(self):
        for version in (1, 3, True, '2'):
            node = copy.deepcopy(self.code); node['typeVersion'] = version
            with self.subTest(version=version), self.assertRaises(sync.Rejected):
                review.preserve_code_v2_for_review(node)
        node = copy.deepcopy(self.code); node['parameters']['unknown'] = 'synthetic'
        with self.assertRaises(sync.Rejected): review.preserve_code_v2_for_review(node)

    def test_nonexecuting_capability_inventory(self):
        probes = {
            'network_http': 'fetch("synthetic-placeholder")',
            'environment_credentials': '$env.SYNTHETIC_NAME',
            'filesystem_process': 'readFile("synthetic-placeholder")',
            'dynamic_evaluation_imports': 'eval("synthetic-placeholder")',
            'database_write_indicators': '/* INSERT INTO synthetic VALUES (1) */',
            'external_service_literal': '/* https' + '://synthetic.invalid */',
            'logging_timers_workflow_state': 'console.log("synthetic")',
            'obfuscation_indicators': 'atob("synthetic-placeholder")',
            'computed_string_member': 'item["synthetic"]',
        }
        for category, source in probes.items():
            node = copy.deepcopy(self.code); node['parameters']['jsCode'] = source
            with self.subTest(category=category):
                result = review.inspect_code_v2(node)
                self.assertTrue(result['capability_indicators'][category])
                self.assertFalse(result['execution_performed'])
                self.assertNotIn(source, json.dumps(result))

    def test_no_signal_does_not_approve_code(self):
        result = review.inspect_code_v2(self.code)
        self.assertEqual(result['assessment'], 'no_flagged_capability_observed')
        self.assertFalse(result['absence_of_capabilities_proven'])
        self.assertFalse(result['conversion_approved'])
        with self.assertRaisesRegex(sync.Rejected, 'EXECUTABLE_NODE_REQUIRES_REVIEW'):
            sync.convert_workflows(sync.encoded([self.workflow]), 'raw', 'unknown')

    def test_scheduler_state_is_unknown_and_preserved(self):
        scheduler = {'name': 'Synthetic scheduler', 'type': 'n8n-nodes-base.scheduleTrigger'}
        self.workflow['nodes'].append(scheduler)
        self.workflow['staticData'] = {'node:Synthetic scheduler': {'recurrenceRules': [None], 'recurrenceRuleSignatures': [None]}}
        before = copy.deepcopy(self.workflow)
        states = review.runtime_state_inventory(self.workflow)
        self.assertEqual(len(states), 2)
        self.assertTrue(all(state['classification'] == 'C' for state in states))
        self.assertTrue(all(state['owner_type'] == 'n8n-nodes-base.scheduleTrigger' for state in states))
        self.assertEqual(self.workflow, before)
        self.assertTrue(all(not state['reset_approved'] for state in states))
        with self.assertRaisesRegex(sync.Rejected, 'UNKNOWN_RUNTIME_STATE'):
            review.require_resolved_runtime_state(self.workflow)

    def test_unknown_state_keys_and_scalars_fail_closed(self):
        for field, value in [('staticData', {'global': {'unknown': 'synthetic'}}),
                             ('pinData', {'synthetic': []}), ('executionData', 'synthetic')]:
            record = copy.deepcopy(self.workflow); record[field] = value
            with self.subTest(field=field):
                self.assertTrue(review.runtime_state_inventory(record))
                with self.assertRaises(sync.Rejected): review.require_resolved_runtime_state(record)

    def test_empty_state_does_not_require_reset(self):
        review.require_resolved_runtime_state(self.workflow)
        self.assertEqual(review.runtime_state_inventory(self.workflow), [])

    def test_version_mismatch_never_substitutes_published_content(self):
        result = review.version_provenance(self.workflow)
        self.assertEqual(result['relation'], 'distinct_current_and_publication_reference')
        self.assertEqual(result['current_version_id'], 'synthetic-current')
        self.assertEqual(result['published_reference_id'], 'synthetic-published')
        self.assertFalse(result['published_body_available'])
        self.assertFalse(result['executing_version_established'])

    def test_equal_reference_is_not_execution_proof(self):
        self.workflow['activeVersionId'] = self.workflow['versionId']
        result = review.version_provenance(self.workflow)
        self.assertEqual(result['relation'], 'matching_reference')
        self.assertFalse(result['executing_version_established'])

    def test_missing_and_contradictory_publication_metadata(self):
        self.workflow.update(active=False, activeVersionId=None)
        self.assertEqual(review.version_provenance(self.workflow)['relation'], 'no_publication_reference')
        self.workflow['activeVersionId'] = 'synthetic-published'
        self.assertEqual(review.version_provenance(self.workflow)['relation'], 'contradictory_inactive_with_publication_reference')
        self.workflow['active'] = 'yes'
        with self.assertRaises(sync.Rejected): review.version_provenance(self.workflow)

    def test_private_original_and_provenance_consistency(self):
        raw = sync.encoded([self.workflow])
        files, report = review.security_payload(raw)
        self.assertEqual(files['workflow-original.private.json'], raw)
        self.assertEqual(review.validate_security_files(files), report)
        self.assertEqual(report['source_sha256'], sync.digest(raw))
        self.assertFalse(report['state_transformation_approved'])
        self.assertNotIn(self.code['parameters']['jsCode'], files['security-review.private.json'].decode())

    def test_rehashed_review_tampering_is_rejected(self):
        files, _ = review.security_payload(sync.encoded([self.workflow]))
        report = sync.decode_json(files['security-review.private.json'])
        report['conversion_approved'] = True
        files['security-review.private.json'] = sync.encoded(report)
        manifest = sync.decode_json(files['manifest.json'])
        manifest['files_sha256']['security-review.private.json'] = sync.digest(files['security-review.private.json'])
        files['manifest.json'] = sync.encoded(manifest)
        with self.assertRaises(sync.Rejected): review.validate_security_files(files)

    def test_extra_or_missing_review_artifacts_rejected(self):
        files, _ = review.security_payload(sync.encoded([self.workflow]))
        extra = dict(files, unexpected=b'synthetic')
        with self.assertRaises(sync.Rejected): review.validate_security_files(extra)
        del files['REVIEW_ONLY']
        with self.assertRaises(sync.Rejected): review.validate_security_files(files)

    def test_original_state_values_remain_in_private_source_only(self):
        self.workflow['staticData'] = {'global': {'unknown': 'SYNTHETIC_PRIVATE_VALUE'}}
        files, report = review.security_payload(sync.encoded([self.workflow]))
        self.assertIn(b'SYNTHETIC_PRIVATE_VALUE', files['workflow-original.private.json'])
        self.assertNotIn('SYNTHETIC_PRIVATE_VALUE', json.dumps(report))
        self.assertEqual(report['workflows'][0]['runtime_state'][0]['classification'], 'C')

    def test_return_array_literals_are_not_member_access(self):
        code = 'if ($json.a) return ["synthetic", $json.a];\nif ($json.b) return ["other", 1];\nreturn ["last", null];'
        contexts = review.bracket_contexts(code)
        self.assertEqual(len(contexts), 3)
        self.assertTrue(all(c['classification'] == 'return_array_literal_not_member_access' for c in contexts))
        self.assertTrue(all(not c['security_clearance'] for c in contexts))

    def test_actual_input_property_pattern_is_not_auto_cleared(self):
        contexts = review.bracket_contexts('return $json["synthetic"];')
        self.assertEqual(contexts[0]['classification'], 'direct_input_property_pattern_requires_content_review')
        self.assertFalse(contexts[0]['security_clearance'])

    def test_comments_templates_and_regex_do_not_fake_return_arrays(self):
        for code in ('// return ["synthetic"]\nreturn [];',
                     'const x = `return ["synthetic"]`; return [];',
                     'const x = /return ["synthetic"]/; return [];',
                     'object.return["synthetic"];'):
            with self.subTest(code=code):
                self.assertFalse(any(c['classification'] == 'return_array_literal_not_member_access'
                                     for c in review.bracket_contexts(code)))

    def test_return_array_classification_never_clears_other_capabilities(self):
        self.code['parameters']['jsCode'] = 'return ["synthetic", fetch("synthetic-placeholder")];'
        result = review.inspect_code_v2(self.code)
        self.assertTrue(result['capability_indicators']['network_http'])
        self.assertTrue(result['capability_indicators']['computed_string_member'])
        self.assertFalse(result['conversion_approved'])

    def test_no_application_reference_is_not_proof_of_state_disposability(self):
        evidence = review.scheduler_reference_trace(self.workflow)
        self.assertEqual(evidence['parameter_settings_text_mentions'], {'recurrenceRules': 0, 'recurrenceRuleSignatures': 0})
        self.assertFalse(evidence['node_internal_implementation_available'])
        for key in ('schedule_generation_effect_established', 'deduplication_effect_established',
                    'reminder_dispatch_effect_established', 'restart_effect_established', 'published_behavior_established'):
            self.assertFalse(evidence[key])

    def test_state_reference_tracing_does_not_modify_or_report_values(self):
        self.workflow['nodes'][0]['parameters']['jsCode'] = '// recurrenceRules recurrenceRuleSignatures\nreturn $input.all();'
        before = copy.deepcopy(self.workflow)
        evidence = review.scheduler_reference_trace(self.workflow)
        self.assertEqual(evidence['parameter_settings_text_mentions'], {'recurrenceRules': 1, 'recurrenceRuleSignatures': 1})
        self.assertEqual(self.workflow, before)

    def test_scheduler_state_preserved_byte_for_byte_with_new_evidence(self):
        self.workflow['nodes'].append({'name': 'Synthetic schedule', 'type': 'n8n-nodes-base.scheduleTrigger'})
        self.workflow['staticData'] = {'node:Synthetic schedule': {'recurrenceRules': [None], 'recurrenceRuleSignatures': [None]}}
        raw = sync.encoded([self.workflow])
        files, report = review.security_payload(raw)
        self.assertEqual(files['workflow-original.private.json'], raw)
        self.assertEqual(sync.decode_json(files['workflow-original.private.json'])[0]['staticData'], self.workflow['staticData'])
        review.validate_security_files(files)
        self.assertFalse(report['state_transformation_approved'])

    def test_inventory_entries_do_not_prove_matching_version_rows(self):
        toc = '1; 1259 123 TABLE public workflow_history synthetic_owner\n2; 0 123 TABLE DATA public workflow_history synthetic_owner\n3; 1259 124 TABLE public credentials_entity synthetic_owner\n'
        inventory = review.version_source_inventory(toc)
        self.assertEqual(len(inventory), 1)
        self.assertEqual(inventory[0]['table'], 'workflow_history')
        self.assertTrue(inventory[0]['data_entry_present'])
        self.assertFalse(inventory[0]['matching_version_row_established'])
        self.assertFalse(inventory[0]['version_body_established'])

    def test_focused_context_reports_do_not_contain_source_text(self):
        self.code['parameters']['jsCode'] = 'return ["SYNTHETIC_PRIVATE_LITERAL", $json.a];'
        result = review.inspect_code_v2(self.code)
        self.assertNotIn('SYNTHETIC_PRIVATE_LITERAL', json.dumps(result))
        self.assertFalse(result['conversion_approved'])


if __name__ == '__main__': unittest.main()
