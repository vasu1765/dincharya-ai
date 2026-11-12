"""Strict offline pg_restore COPY-text inspection. Never executes SQL or JS."""
import re
from source_sync import Rejected, decode_json, encoded, validate_schema, sql_statements
from version_evidence import AUTHORIZED_TABLES, comparable_json, resolve_versions

COLUMNS = {
    'workflow_history': ('versionId', 'workflowId', 'authors', 'createdAt', 'updatedAt',
                         'nodes', 'connections', 'name', 'autosaved', 'description', 'nodeGroups'),
    'workflow_publish_history': ('id', 'workflowId', 'versionId', 'event', 'userId', 'createdAt'),
    'workflow_published_version': ('workflowId', 'publishedVersionId', 'createdAt', 'updatedAt'),
}


def decode_copy_field(value):
    if value == r'\N':
        return None
    source = value.encode('utf-8')
    result = bytearray()
    i = 0
    escapes = {ord('b'): 8, ord('f'): 12, ord('n'): 10, ord('r'): 13,
               ord('t'): 9, ord('v'): 11, ord('\\'): 92}
    while i < len(source):
        if source[i] != 92:
            result.append(source[i]); i += 1; continue
        i += 1
        if i == len(source):
            raise Rejected('TRUNCATED_COPY_ESCAPE')
        char = source[i]
        if char in escapes:
            result.append(escapes[char]); i += 1
        elif ord('0') <= char <= ord('7'):
            match = re.match(rb'[0-7]{1,3}', source[i:])
            number = int(match.group(), 8)
            if number > 255:
                raise Rejected('INVALID_COPY_OCTAL')
            result.append(number); i += len(match.group())
        elif char == ord('x'):
            match = re.match(rb'[0-9a-fA-F]{1,2}', source[i+1:])
            if not match:
                raise Rejected('INVALID_COPY_HEX')
            result.append(int(match.group(), 16)); i += 1 + len(match.group())
        else:
            raise Rejected('UNSUPPORTED_COPY_ESCAPE')
    try:
        return result.decode('utf-8')
    except UnicodeError:
        raise Rejected('INVALID_COPY_ENCODING') from None


def parse_extraction(content):
    text = content.decode('utf-8')
    outside, rows, current, columns = [], {}, None, None
    for line in text.splitlines(keepends=True):
        if current is not None:
            if line.rstrip('\r\n') == r'\.':
                current, columns = None, None
                continue
            fields = line.rstrip('\r\n').split('\t')
            if len(fields) != len(columns):
                raise Rejected('COPY_COLUMN_COUNT_MISMATCH')
            rows[current].append(dict(zip(columns, (decode_copy_field(value) for value in fields))))
            continue
        match = re.fullmatch(r'COPY public\.([A-Za-z_][A-Za-z0-9_]*) \(([^\r\n]+)\) FROM stdin;\r?\n?', line)
        if match:
            table = match.group(1)
            if table not in AUTHORIZED_TABLES or table in rows:
                raise Rejected('UNAUTHORIZED_OR_DUPLICATE_COPY_TABLE')
            parsed_columns = []
            for name in match.group(2).split(', '):
                identifier = re.fullmatch(r'"([A-Za-z_][A-Za-z0-9_]*)"|([a-z_][a-z0-9_]*)', name)
                if not identifier:
                    raise Rejected('INVALID_COPY_COLUMN_IDENTIFIER')
                parsed_columns.append(identifier.group(1) or identifier.group(2))
            if tuple(parsed_columns) != COLUMNS[table]:
                raise Rejected('UNREVIEWED_TABLE_COLUMN_LAYOUT')
            rows[table] = []
            current, columns = table, parsed_columns
        else:
            if line.lstrip().startswith('COPY '):
                raise Rejected('UNSUPPORTED_COPY_STATEMENT')
            outside.append(line)
    if current is not None or set(rows) != AUTHORIZED_TABLES:
        raise Rejected('INCOMPLETE_AUTHORIZED_COPY_SET')
    ddl = ''.join(outside)
    validate_schema(ddl.encode())
    framed = sql_statements('\n'.join(line for line in ddl.splitlines() if not line.lstrip().startswith('\\')))
    tables = set()
    for statement in framed:
        match = re.match(r'^CREATE TABLE public\.([A-Za-z_][A-Za-z0-9_]*)\s*\(', statement)
        if match:
            table = match.group(1)
            if table not in AUTHORIZED_TABLES or table in tables:
                raise Rejected('UNAUTHORIZED_OR_DUPLICATE_DEFINITION')
            tables.add(table)
        elif not re.match(r'^(?:SET\s|SELECT pg_catalog\.set_config\s*\()', statement):
            raise Rejected('UNEXPECTED_EXTRACTION_STATEMENT')
    if tables != AUTHORIZED_TABLES:
        raise Rejected('MISSING_AUTHORIZED_DEFINITION')
    return rows


def definition_diff(current_nodes, published_nodes):
    maps = []
    for nodes in (current_nodes, published_nodes):
        identities = [node.get('id') for node in nodes if isinstance(node, dict)]
        if len(identities) != len(nodes) or any(not isinstance(value, str) for value in identities) or len(set(identities)) != len(identities):
            raise Rejected('AMBIGUOUS_NODE_IDENTITY_FOR_COMPARISON')
        maps.append(dict(zip(identities, nodes)))
    current, published = maps
    changes, code_changes = {}, 0
    for identity in current.keys() & published.keys():
        before, after = published[identity], current[identity]
        for field in before.keys() | after.keys():
            if comparable_json(before.get(field)) != comparable_json(after.get(field)):
                changes[field] = changes.get(field, 0) + 1
        if (after.get('type') == 'n8n-nodes-base.code'
                and before.get('parameters', {}).get('jsCode') != after.get('parameters', {}).get('jsCode')):
            code_changes += 1
    return {'added_node_count': len(current.keys() - published.keys()),
            'removed_node_count': len(published.keys() - current.keys()),
            'changed_node_field_counts': changes, 'changed_code_body_count': code_changes,
            'runtime_behavior_equivalence_established': False}


def analyze_versions(snapshot_raw, sql_raw, archive_sha256):
    """Use explicit observed columns; publication events are never treated as current."""
    from source_sync import digest, convert_workflows
    snapshots = decode_json(snapshot_raw)
    if not isinstance(snapshots, list) or not snapshots:
        raise Rejected('EXPECTED_WORKFLOW_SNAPSHOT_ARRAY')
    identities = [record.get('id') for record in snapshots if isinstance(record, dict)]
    if len(identities) != len(snapshots) or any(not isinstance(v, str) for v in identities) or len(set(identities)) != len(identities):
        raise Rejected('INVALID_OR_DUPLICATE_WORKFLOW_ID')
    tables = parse_extraction(sql_raw)
    histories, publications, references = [], {}, []
    historical_records = {}
    for row in tables['workflow_history']:
        nodes, connections, groups = (decode_json(row[key]) if row[key] is not None else None for key in ('nodes', 'connections', 'nodeGroups'))
        if not isinstance(nodes, list) or not isinstance(connections, dict) or groups is not None and not isinstance(groups, list):
            raise Rejected('INVALID_HISTORY_JSON_STRUCTURE')
        key = (row['workflowId'], row['versionId'])
        if key in historical_records and historical_records[key] != row:
            raise Rejected('DUPLICATE_HISTORY_RECORD_CONFLICT')
        historical_records[key] = row
        histories.append({'workflow_id': row['workflowId'], 'version_id': row['versionId'],
                          'content': {'nodes': nodes, 'connections': connections}})
    for row in tables['workflow_published_version']:
        identity = row['workflowId']
        if identity in publications:
            raise Rejected('DUPLICATE_CURRENT_PUBLICATION_ROW')
        publications[identity] = row['publishedVersionId']
        references.append({'workflow_id': identity, 'version_id': row['publishedVersionId'],
                           'role': 'current', 'source_table': 'workflow_published_version'})
    unversioned_events = []
    for row in tables['workflow_publish_history']:
        if row['event'] not in {'activated', 'deactivated'}:
            raise Rejected('UNREVIEWED_PUBLICATION_EVENT')
        if row['versionId'] is None:
            # A versionless historical event cannot identify a workflow body.
            # Preserve either event kind without substituting any version ID.
            unversioned_events.append(row)
        else:
            references.append({'workflow_id': row['workflowId'], 'version_id': row['versionId'],
                               'role': 'historical', 'source_table': 'workflow_publish_history'})
    event_keys = {(row['workflowId'], row['versionId']) for row in tables['workflow_publish_history']
                  if row['versionId'] is not None}
    event_references = [{'workflow_id': identity, 'version_id': version,
                         'body_available': (identity, version) in historical_records,
                         'role': 'historical_event_reference_not_current_publication'}
                        for identity, version in sorted(event_keys)]
    resolutions, bodies, candidates, provenance, rejections = [], [], [], [], []
    for index, record in enumerate(snapshots, 1):
        result = resolve_versions(record, histories, references, archive_sha256, digest(snapshot_raw))
        result['production_schema_mapping_verified'] = True
        result['mapping_scope'] = 'observed_exact_COPY_columns_no_runtime_compatibility_claim'
        result['source_index'] = index
        current_history = historical_records.get((record['id'], record['versionId']))
        result['current_history_body_present'] = current_history is not None
        result['current_history_differences'] = ({key: comparable_json(record[key]) != comparable_json(decode_json(current_history[key]))
                                                for key in ('nodes', 'connections')} if current_history else {})
        pub = result['published_reference_id']
        if pub:
            original = historical_records.get((record['id'], pub))
            if original is not None:
                result['node_definition_diff'] = definition_diff(record['nodes'], decode_json(original['nodes']))
                bodies.append({'source_index': index, 'role': 'published_reference_body',
                               'original_history_record': original,
                               'decoded_nodes': decode_json(original['nodes']),
                               'decoded_connections': decode_json(original['connections']),
                               'settings_available': False, 'runtime_state_available': False,
                               'import_compatibility_verified': False})
        resolutions.append(result)
        try:
            converted, metadata = convert_workflows(encoded([record]), 'raw', 'unknown')
        except Rejected as error:
            rejections.append({'source_index': index, 'category': str(error)})
        else:
            candidates.extend(converted)
            provenance.append({'source_index': index, 'role': 'current_snapshot_only', **metadata[0]})
    return {'tables': tables, 'resolutions': resolutions, 'published_bodies': bodies,
            'unversioned_events': unversioned_events,
            'event_references': event_references,
            'current_candidates': candidates, 'current_provenance': provenance, 'rejections': rejections,
            'history_row_count': len(tables['workflow_history']),
            'relevant_history_count': sum(r['relevant_unique_history_count'] for r in resolutions),
            'publication_reference_count': len(publications),
            'source_promotion_approved': False, 'execution_performed': False,
            'scheduler_state_modified': False}
