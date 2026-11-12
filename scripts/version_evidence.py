"""Offline evidence logic for explicitly normalized rows; no archive/SQL executor.

Actual n8n table definitions must be inspected and a schema mapping reviewed
before real extracted rows can be supplied. This module never opens a dump.
"""
import copy
import json
import re
from source_sync import Rejected, decode_json, digest, encoded

AUTHORIZED_TABLES = frozenset({'workflow_history', 'workflow_published_version', 'workflow_publish_history'})


def comparable_json(value):
    """Ignore JSON object-key serialization order, preserve arrays/scalar types/text.

    Original artifacts are never rewritten; this representation is only for diffs.
    """
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def plan_authorized_toc(toc):
    """Plan only exact public TABLE/TABLE DATA entries from pg_restore --list.

    This is not a substitute for obtaining that list from the verified archive.
    No dependencies, ACLs, comments, constraints or other tables are selected.
    """
    selected = {}
    for line in toc.splitlines():
        match = re.match(r'^(\d+);\s+\d+\s+\d+\s+(TABLE DATA|TABLE)\s+(\S+)\s+(\S+)\s+', line)
        if not match or match.group(4) not in AUTHORIZED_TABLES:
            continue
        entry_id, kind, schema, table = match.groups()
        if schema != 'public':
            raise Rejected('AMBIGUOUS_AUTHORIZED_TABLE_SCHEMA')
        key = (table, kind)
        if key in selected:
            raise Rejected('DUPLICATE_AUTHORIZED_TOC_ENTRY')
        selected[key] = {'entry_id': int(entry_id), 'kind': kind, 'schema': schema, 'table': table}
    required = {(table, kind) for table in AUTHORIZED_TABLES for kind in ('TABLE', 'TABLE DATA')}
    if set(selected) != required:
        raise Rejected('MISSING_AUTHORIZED_TOC_ENTRY')
    if len({entry['entry_id'] for entry in selected.values()}) != len(selected):
        raise Rejected('DUPLICATE_TOC_IDENTIFIER')
    return sorted(selected.values(), key=lambda entry: entry['entry_id'])


def require_hash(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise Rejected('INVALID_EVIDENCE_DIGEST')


def require_id(value):
    if not isinstance(value, str) or not value:
        raise Rejected('INVALID_EVIDENCE_IDENTIFIER')


def resolve_versions(snapshot, histories, references, archive_sha256, snapshot_sha256):
    """Compare normalized evidence, never infer executing version or reset state.

    Histories: workflow_id, version_id, content (nodes/connections; settings optional).
    References: workflow_id, version_id, role=current|historical, source_table.
    These names are an internal contract, NOT assumed n8n database columns.
    """
    require_hash(archive_sha256)
    require_hash(snapshot_sha256)
    if (not isinstance(snapshot, dict) or not isinstance(histories, list)
            or not isinstance(references, list) or not isinstance(snapshot.get('nodes'), list)
            or not isinstance(snapshot.get('connections'), dict)):
        raise Rejected('INVALID_NORMALIZED_EVIDENCE')
    workflow_id, current_id, snapshot_reference = snapshot.get('id'), snapshot.get('versionId'), snapshot.get('activeVersionId')
    require_id(workflow_id)
    require_id(current_id)
    if type(snapshot.get('active')) is not bool:
        raise Rejected('INVALID_PUBLICATION_METADATA')
    if snapshot_reference is not None:
        require_id(snapshot_reference)
        if snapshot['active'] is False:
            raise Rejected('CONTRADICTORY_PUBLICATION_METADATA')
    versions = {}
    for row in histories:
        if not isinstance(row, dict) or set(row) != {'workflow_id', 'version_id', 'content'}:
            raise Rejected('INVALID_NORMALIZED_HISTORY')
        require_id(row['workflow_id'])
        require_id(row['version_id'])
        content = row['content']
        if (not isinstance(content, dict) or set(content) - {'nodes', 'connections', 'settings'}
                or not isinstance(content.get('nodes'), list) or not isinstance(content.get('connections'), dict)
                or 'settings' in content and not isinstance(content['settings'], dict)):
            raise Rejected('INCOMPLETE_NORMALIZED_BODY')
        if row['workflow_id'] != workflow_id:
            continue
        version = row['version_id']
        if version in versions and comparable_json(versions[version]) != comparable_json(content):
            raise Rejected('CONFLICTING_VERSION_BODIES')
        versions[version] = copy.deepcopy(content)
    current_references, historical_references = set(), set()
    for row in references:
        if (not isinstance(row, dict) or set(row) != {'workflow_id', 'version_id', 'role', 'source_table'}
                or not isinstance(row['source_table'], str) or not isinstance(row['role'], str)
                or row['source_table'] not in AUTHORIZED_TABLES - {'workflow_history'}
                or row['role'] not in {'current', 'historical'}):
            raise Rejected('INVALID_NORMALIZED_PUBLICATION_REFERENCE')
        require_id(row['workflow_id'])
        require_id(row['version_id'])
        if row['workflow_id'] == workflow_id:
            (current_references if row['role'] == 'current' else historical_references).add(row['version_id'])
    if len(current_references) > 1:
        raise Rejected('CONFLICTING_CURRENT_PUBLICATION_REFERENCES')
    table_reference = next(iter(current_references), None)
    if snapshot_reference and table_reference and snapshot_reference != table_reference:
        raise Rejected('SNAPSHOT_PUBLICATION_REFERENCE_CONFLICT')
    published_id = snapshot_reference or table_reference
    body = versions.get(published_id)
    compared = sorted(body) if body is not None else []
    differences = {key: comparable_json(snapshot.get(key)) != comparable_json(body[key]) for key in compared}
    return {
        'workflow_id': workflow_id, 'current_version_id': current_id,
        'published_reference_id': published_id,
        'relevant_unique_history_count': len(versions),
        'history_version_ids': sorted(versions),
        'historical_publication_reference_ids': sorted(historical_references),
        'published_body_located': body is not None,
        'body_status': 'located_in_normalized_history' if body is not None else (
            'missing_referenced_body' if published_id else 'publication_reference_unavailable'),
        'compared_fields': compared, 'differences_by_field': differences,
        'current_published_differ_on_compared_fields': any(differences.values()) if body is not None else None,
        'full_content_comparison_complete': body is not None and set(body) == {'nodes', 'connections', 'settings'},
        'executing_version_established': False,
        'state_treatment_approved': False, 'source_promotion_approved': False,
        'production_schema_mapping_verified': False,
        'archive_sha256': archive_sha256, 'snapshot_sha256': snapshot_sha256,
    }


def version_report_payload(snapshot_raw, normalized_raw):
    """Private evidence contract with originals; no automatic output or promotion."""
    snapshot, normalized = decode_json(snapshot_raw), decode_json(normalized_raw)
    if not isinstance(normalized, dict) or set(normalized) != {'histories', 'references', 'archive_sha256'}:
        raise Rejected('INVALID_NORMALIZED_EVIDENCE')
    result = resolve_versions(snapshot, normalized['histories'], normalized['references'],
                              normalized['archive_sha256'], digest(snapshot_raw))
    files = {'snapshot.private.json': snapshot_raw, 'normalized.private.json': normalized_raw,
             'resolution.private.json': encoded(result)}
    files['manifest.json'] = encoded({'kind': 'normalized_version_evidence_v1',
                                     'files_sha256': {name: digest(value) for name, value in files.items()},
                                     'database_access_performed': False, 'archive_extraction_performed': False})
    return files, result


def validate_version_report(files):
    if not {'snapshot.private.json', 'normalized.private.json'} <= set(files):
        raise Rejected('MISSING_VERSION_EVIDENCE_ORIGINALS')
    expected, result = version_report_payload(files['snapshot.private.json'], files['normalized.private.json'])
    if expected != files:
        raise Rejected('VERSION_EVIDENCE_PROVENANCE_MISMATCH')
    return result
