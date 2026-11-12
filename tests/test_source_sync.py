import importlib.util
import json
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('source_sync', ROOT / 'scripts/source_sync.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SourcePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.schema = ROOT / 'tests/fixtures/schema.sql'
        self.workflow = self.root / 'input.json'
        self.records = json.loads((ROOT / 'tests/fixtures/workflow.raw.json').read_text())

    def prepare(self, reviewed=True, state='draft'):
        self.workflow.write_text(json.dumps(self.records))
        return sync.prepare(self.schema, self.workflow, self.root / 'public',
                            self.root / 'private', 'raw', state, reviewed, self.root)

    def validate(self):
        return sync.validate_bundle(self.root / 'public', self.root / 'private', self.root)

    def test_preserves_schema_expressions_connections_and_private_identity(self):
        self.prepare()
        self.validate()
        public = json.loads((self.root / 'public/workflows.candidate.json').read_text())[0]
        private = json.loads((self.root / 'private/workflow-provenance.private.json').read_text())[0]
        self.assertEqual((self.root / 'public/application-schema.sql').read_bytes(), self.schema.read_bytes())
        self.assertEqual(public['connections'], self.records[0]['connections'])
        self.assertEqual(public['nodes'], self.records[0]['nodes'])
        self.assertFalse(public['active'])
        self.assertNotIn('id', public)
        self.assertEqual(private['original_record'], self.records[0])
        self.assertFalse(private['state_verified'])
        self.assertEqual((self.root / 'private').stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.root / 'public/application-schema.sql').stat().st_mode & 0o777, 0o600)

    def test_review_attestation_required(self):
        with self.assertRaises(sync.Rejected):
            self.prepare(reviewed=False)
        self.assertFalse((self.root / 'public').exists())

    def test_raw_published_provenance_rejected(self):
        with self.assertRaises(sync.Rejected):
            self.prepare(state='published')

    def test_sensitive_fields_rejected_without_outputs(self):
        for key in ('credentials', 'pinData', 'staticData', 'executionData', 'unknownField'):
            with self.subTest(key=key):
                self.records[0][key] = {'synthetic': 'sensitive-example'}
                with self.assertRaises(sync.Rejected):
                    self.prepare()
                del self.records[0][key]
                self.assertFalse((self.root / 'private').exists())

    def test_invalid_connection_rejected(self):
        self.records[0]['connections']['Start']['main'][0][0]['node'] = 'Missing'
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_duplicate_nodes_rejected(self):
        self.records[0]['nodes'][1]['name'] = 'Start'
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_code_node_rejected(self):
        self.records[0]['nodes'][0]['type'] = 'n8n-nodes-base.code'
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_no_overwrite(self):
        self.prepare()
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_tampering_detected(self):
        self.prepare()
        with (self.root / 'public/application-schema.sql').open('a') as stream:
            stream.write('\n-- changed\n')
        with self.assertRaises(sync.Rejected):
            self.validate()

    def test_connection_string_and_private_key_detection(self):
        # Construct synthetic detector probes at runtime; no credential-like
        # complete strings are stored as source literals.
        for value in ('postgresql://' + 'user:' + 'synthetic-password' + '@localhost/db',
                      '-----BEGIN ' + 'PRIVATE KEY-----'):
            with self.subTest(value=value), self.assertRaises(sync.Rejected):
                sync.scan_text(value)

    def test_schema_data_dump_rejected(self):
        bad = self.root / 'bad.sql'
        bad.write_text('CREATE TABLE example(id int);\nCOPY example FROM stdin;\n')
        with self.assertRaises(sync.Rejected):
            sync.load_schema(bad)

    def test_duplicate_json_key_rejected(self):
        self.workflow.write_text('{"id":"first","id":"second"}')
        with self.assertRaises(sync.Rejected):
            sync.load_workflows(self.workflow, 'raw', 'draft')

    def test_private_output_inside_project_rejected(self):
        self.workflow.write_text(json.dumps(self.records))
        with self.assertRaises(sync.Rejected):
            sync.prepare(self.schema, self.workflow, self.root / 'public',
                         ROOT / 'private-test-never-created', 'raw', 'draft', True, self.root)

    def test_unknown_node_rejected(self):
        self.records[0]['nodes'][0]['type'] = 'unreviewed-community.custom'
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_auth_header_rejected(self):
        self.records[0]['nodes'][0]['parameters'] = {'headers': [{'name': 'Authorization', 'value': 'synthetic'}]}
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_nonfinite_number_rejected(self):
        self.records[0]['nodes'][0]['parameters']['value'] = float('inf')
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_private_parent_permissions_rejected(self):
        self.root.chmod(0o755)
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_private_parent_git_repository_rejected(self):
        marker = self.root / '.git'
        marker.mkdir()
        (marker / 'HEAD').write_text('ref: refs/heads/synthetic\n')
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_cli_errors_do_not_echo_input(self):
        from unittest.mock import patch
        self.records[0]['pinData'] = {'private': 'SYNTHETIC_DO_NOT_ECHO'}
        self.workflow.write_text(json.dumps(self.records))
        args = ['source_sync.py', '--schema', str(self.schema), '--workflow', str(self.workflow),
                '--output', str(self.root / 'public'), '--private-output', str(self.root / 'private'),
                '--input-format', 'raw', '--state', 'unknown', '--reviewed-inputs', '--private-root', str(self.root)]
        output, errors = io.StringIO(), io.StringIO()
        with patch('sys.argv', args), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(sync.main(), 1)
        self.assertNotIn('SYNTHETIC_DO_NOT_ECHO', output.getvalue() + errors.getvalue())
        self.assertEqual(output.getvalue(), '')


class HardenedPreparationTests(unittest.TestCase):
    setUp = SourcePreparationTests.setUp
    prepare = SourcePreparationTests.prepare
    validate = SourcePreparationTests.validate
    def mutate_manifest(self, change):
        path = self.root / 'public/manifest.json'
        manifest = json.loads(path.read_text())
        change(manifest)
        path.write_bytes(sync.encoded(manifest))

    def test_api_key_variants_rejected(self):
        for key in ('apiKey', 'api_key', 'API-KEY', 'xApiKey'):
            with self.subTest(key=key):
                self.records[0]['nodes'][1]['parameters']['value'] = {key: 'opaque-synthetic-value'}
                with self.assertRaises(sync.Rejected):
                    self.prepare()
                self.assertFalse((self.root / 'public').exists())

    def test_unknown_nested_node_field_rejected(self):
        self.records[0]['nodes'][0]['unreviewedPayload'] = 'opaque'
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_unknown_parameter_and_settings_rejected(self):
        self.records[0]['nodes'][1]['parameters']['unreviewed'] = 1
        with self.assertRaises(sync.Rejected):
            self.prepare()
        del self.records[0]['nodes'][1]['parameters']['unreviewed']
        self.records[0]['settings']['errorWorkflow'] = 'private-workflow-id'
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_duplicate_node_id_rejected(self):
        self.records[0]['nodes'][1]['id'] = self.records[0]['nodes'][0]['id']
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_unreviewed_node_version_rejected(self):
        self.records[0]['nodes'][1]['typeVersion'] = 999
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_publication_metadata_types_rejected(self):
        for key, value in [('active', 'yes'), ('versionId', {}), ('versionMetadata', {'unknown': 'value'})]:
            with self.subTest(key=key):
                original = self.records[0].get(key)
                self.records[0][key] = value
                with self.assertRaises(sync.Rejected):
                    self.prepare()
                if original is None:
                    self.records[0].pop(key)
                else:
                    self.records[0][key] = original

    def test_editor_published_contradiction_rejected(self):
        raw = sync.encoded(self.records)
        with self.assertRaises(sync.Rejected):
            sync.convert_workflows(raw, 'editor', 'published')
        self.records[0]['activeVersionId'] = self.records[0]['versionId']
        candidates, metadata = sync.convert_workflows(sync.encoded(self.records), 'editor', 'published')
        self.assertFalse(candidates[0]['active'])
        self.assertFalse(metadata[0]['state_verified'])

    def test_credential_references_private_and_verifiable(self):
        reference = {'postgres': {'id': 'synthetic-reference', 'name': 'Synthetic database'}}
        self.records[0]['nodes'][1]['credentials'] = reference
        self.prepare()
        self.validate()
        candidate = json.loads((self.root / 'public/workflows.candidate.json').read_text())
        metadata = json.loads((self.root / 'private/workflow-provenance.private.json').read_text())
        self.assertNotIn('credentials', candidate[0]['nodes'][1])
        self.assertEqual(metadata[0]['credential_references']['synthetic-node-2'], reference)
        self.assertEqual(metadata[0]['original_record'], self.records[0])

    def test_credential_values_not_accepted_as_references(self):
        self.records[0]['nodes'][1]['credentials'] = {'postgres': {'id': 'synthetic', 'name': 'Synthetic', 'pass' + 'word': 'opaque'}}
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_embedded_reference_stays_private_without_rewriting(self):
        self.records[0]['nodes'][1]['parameters']['value'] = '={{ "private-workflow-id" + $json.message }}'
        self.prepare()
        candidate = json.loads((self.root / 'public/workflows.candidate.json').read_text())
        self.assertEqual(candidate[0]['nodes'][1]['parameters'], self.records[0]['nodes'][1]['parameters'])
        self.assertFalse((ROOT / 'database/baseline/review-candidate').exists())

    def test_manifest_flags_enforced_even_with_valid_hashes(self):
        self.prepare()
        for key in ('promotion_approved', 'import_compatibility_verified', 'database_execution_performed', 'state_verified'):
            with self.subTest(key=key):
                self.mutate_manifest(lambda m: m.update({key: True}))
                with self.assertRaises(sync.Rejected):
                    self.validate()
                self.mutate_manifest(lambda m: m.update({key: False}))
        self.mutate_manifest(lambda m: m.update(workflow_count=True))
        with self.assertRaises(sync.Rejected):
            self.validate()

    def test_private_metadata_tampering_rejected(self):
        self.prepare()
        path = self.root / 'private/workflow-provenance.private.json'
        data = json.loads(path.read_text())
        data[0]['declared_state'] = 'published'
        path.write_bytes(sync.encoded(data))
        # Even rehashing does not authorize a provenance contradiction.
        self.mutate_manifest(lambda m: m.update(provenance_sha256=sync.digest(path.read_bytes())))
        with self.assertRaises(sync.Rejected):
            self.validate()

    def test_public_identity_injection_rejected_after_rehash(self):
        self.prepare()
        path = self.root / 'public/workflows.candidate.json'
        data = json.loads(path.read_text())
        data[0]['id'] = 'injected'
        path.write_bytes(sync.encoded(data))
        self.mutate_manifest(lambda m: m.update(workflow_source_sha256=sync.digest(path.read_bytes())))
        with self.assertRaises(sync.Rejected):
            self.validate()

    def test_marker_and_unexpected_files_rejected(self):
        self.prepare()
        marker = self.root / 'public/PREPARED'
        marker.write_bytes(b'incorrect')
        with self.assertRaises(sync.Rejected):
            self.validate()
        marker.write_bytes(sync.MARKER)
        (self.root / 'public/unexpected').write_text('synthetic')
        with self.assertRaises(sync.Rejected):
            self.validate()

    def test_symlink_input_rejected(self):
        link = self.root / 'link.sql'
        link.symlink_to(self.schema)
        with self.assertRaises(OSError):
            sync.load_schema(link)

    def test_symlink_output_and_escape_rejected(self):
        self.workflow.write_bytes(sync.encoded(self.records))
        (self.root / 'public').symlink_to(self.root / 'elsewhere')
        with self.assertRaises(sync.Rejected):
            self.prepare()
        with self.assertRaises(sync.Rejected):
            sync.prepare(self.schema, self.workflow, self.root.parent / 'escape',
                         self.root / 'metadata-other', 'raw', 'unknown', True, self.root)

    def test_private_root_symlink_rejected(self):
        link = self.root / 'link-root'
        link.symlink_to(self.root, target_is_directory=True)
        self.workflow.write_bytes(sync.encoded(self.records))
        with self.assertRaises(sync.Rejected):
            sync.prepare(self.schema, self.workflow, link / 'bundle', link / 'metadata',
                         'raw', 'unknown', True, link)

    def test_bare_repository_private_root_rejected(self):
        (self.root / 'HEAD').write_text('ref: refs/heads/synthetic\n')
        (self.root / 'objects').mkdir()
        (self.root / 'refs').mkdir()
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_partial_write_has_no_prepared_marker(self):
        from unittest.mock import patch
        original = sync.write_file
        def fail_schema(fd, name, content):
            if name == 'application-schema.sql':
                raise OSError('synthetic I/O failure with private details')
            return original(fd, name, content)
        with patch.object(sync, 'write_file', side_effect=fail_schema):
            with self.assertRaises(OSError):
                self.prepare()
        self.assertFalse((self.root / 'public/PREPARED').exists())
        with self.assertRaises(sync.Rejected):
            self.validate()

    def test_each_bundle_file_read_once(self):
        from unittest.mock import patch
        self.prepare()
        with patch.object(sync, 'read_fd', wraps=sync.read_fd) as reader:
            self.validate()
            self.assertEqual(reader.call_count, 6)

    def test_symlink_payload_and_bad_permissions_rejected(self):
        self.prepare()
        marker = self.root / 'public/PREPARED'
        marker.chmod(0o644)
        with self.assertRaises(sync.Rejected):
            self.validate()
        marker.chmod(0o600)
        marker.unlink()  # Own synthetic temporary fixture only.
        marker.symlink_to(self.root / 'private/workflow-input.private.json')
        with self.assertRaises(OSError):
            self.validate()

    def test_psql_directives_and_top_level_data_rejected(self):
        for tail in ('\\! echo synthetic', '\\i external.sql', '\\gexec',
                     "INSERT INTO x VALUES ('synthetic');", 'DO $$ BEGIN END; $$;'):
            with self.subTest(tail=tail), self.assertRaises(sync.Rejected):
                sync.validate_schema(('CREATE TABLE x(id int);\n' + tail + '\n').encode())

    def test_function_insert_body_preserved(self):
        schema = b'CREATE TABLE x(id int);\nCREATE FUNCTION f() RETURNS void LANGUAGE sql AS $$\nINSERT INTO x VALUES (1);\n$$;\n'
        self.assertEqual(sync.validate_schema(schema), schema)

    def test_truncated_sql_and_secret_literals_rejected(self):
        for schema in (b'CREATE TABLE x(id int)', b'CREATE FUNCTION f() RETURNS text AS $$ truncated',
                       b"CREATE TABLE x(id int); COMMENT ON TABLE x IS '" + b'pass' + b"word=opaque-synthetic';"):
            with self.subTest(schema=schema), self.assertRaises(sync.Rejected):
                sync.validate_schema(schema)

    def test_pg_dump_restrict_pair_preserved(self):
        schema = b'\\restrict synthetic\nCREATE TABLE x(id int);\n\\unrestrict synthetic\n'
        self.assertEqual(sync.validate_schema(schema), schema)
        with self.assertRaises(sync.Rejected):
            sync.validate_schema(schema.replace(b'unrestrict synthetic', b'unrestrict mismatch'))

    def test_validator_cli_reports_safe_failure(self):
        from unittest.mock import patch
        validator_spec = importlib.util.spec_from_file_location('validator', ROOT / 'scripts/validate-source.py')
        module = importlib.util.module_from_spec(validator_spec)
        with patch.dict('sys.modules', {'source_sync': sync}):
            validator_spec.loader.exec_module(module)
        output, errors = io.StringIO(), io.StringIO()
        args = ['validate-source.py', '--bundle', str(self.root / 'missing'),
                '--private-metadata', str(self.root / 'private'), '--private-root', str(self.root)]
        with patch('sys.argv', args), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(module.main(), 1)
        self.assertEqual(output.getvalue(), '')
        self.assertNotIn(str(self.root), errors.getvalue())

    def test_fixture_compose_is_standalone_and_ephemeral(self):
        config = (ROOT / 'tests/compose.test.yaml').read_text()
        for forbidden in ('external:', 'env_file:', 'ports:', 'volumes:', 'docker.sock', '${'):
            self.assertNotIn(forbidden, config)
        self.assertIn('internal: true', config)
        self.assertIn('tmpfs:', config)
        self.assertNotIn('telegram', config.lower())

    def test_nested_set_structures_fail_closed(self):
        for parameters in ({'options': {'unknown': True}},
                           {'assignments': {'unknown': []}},
                           {'assignments': {'assignments': [{'name': 'missing-required-fields'}]}}):
            self.records[0]['nodes'][1]['parameters'] = parameters
            with self.subTest(parameters=parameters), self.assertRaises(sync.Rejected):
                self.prepare()

    def test_invalid_connection_port_rejected(self):
        self.records[0]['connections']['Start']['main'][0][0]['index'] = 1
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_boolean_numeric_substitution_rejected_after_rehash(self):
        self.records[0]['nodes'][1]['parameters']['value'] = 1
        self.prepare()
        path = self.root / 'public/workflows.candidate.json'
        data = json.loads(path.read_text())
        data[0]['nodes'][1]['parameters']['value'] = True
        path.write_bytes(sync.encoded(data))
        self.mutate_manifest(lambda m: m.update(workflow_source_sha256=sync.digest(path.read_bytes())))
        with self.assertRaises(sync.Rejected):
            self.validate()

    def test_oversized_coordinate_rejected_safely(self):
        self.records[0]['nodes'][0]['position'] = [10 ** 500, 0]
        with self.assertRaises(sync.Rejected):
            self.prepare()

    def test_cli_argument_errors_do_not_echo_values(self):
        parser = sync.SafeArgumentParser()
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors), self.assertRaises(SystemExit):
            parser.parse_args(['--unsupported=SYNTHETIC_PRIVATE_ARGUMENT'])
        self.assertNotIn('SYNTHETIC_PRIVATE_ARGUMENT', errors.getvalue())

    def test_safe_source_scanner_rejects_secret_paths_before_open(self):
        from unittest.mock import patch
        scanner_spec = importlib.util.spec_from_file_location('scanner', ROOT / 'scripts/check-safe-source.py')
        scanner = importlib.util.module_from_spec(scanner_spec)
        with patch.dict('sys.modules', {'source_sync': sync}):
            scanner_spec.loader.exec_module(scanner)
        for path in (ROOT / '.env', ROOT / 'backups/unread.sql', ROOT / 'workflow-input.private.json',
                     ROOT / 'extracted-tables.original.private.sql'):
            with self.subTest(path=path), patch.object(scanner, 'read_input') as reader:
                with self.assertRaises(sync.Rejected):
                    scanner.check_path(path)
                reader.assert_not_called()


if __name__ == '__main__':
    unittest.main()
