"""Non-executing private workflow inspection; never approves conversion or state reset."""
import copy
import re
from source_sync import Rejected, digest, decode_json, encoded, NODE_FIELDS

CAPABILITY_PATTERNS = {
    'network_http': r'(?i)\b(?:fetch|axios|https?|XMLHttpRequest|WebSocket)\b|\$http|httpRequest',
    'environment_credentials': r'(?i)\$env|process\s*[.\[]|\$credentials|getCredentials|\bcredentials?\b',
    'filesystem_process': r'(?i)\b(?:fs|child_process|spawn|execSync|readFile|writeFile|Deno|Bun)\b',
    'dynamic_evaluation_imports': r'\b(?:require|import|eval|Function)\s*\(|\bimport\s|\b(?:globalThis|Reflect)\b|constructor\s*[.(\[]',
    'database_write_indicators': r'(?i)\b(?:INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|DROP\s+TABLE|pg_query|executeQuery)\b',
    'external_service_literal': r'(?i)(?:https?|wss?|postgres(?:ql)?|redis|mongodb)://',
    'logging_timers_workflow_state': r'\b(?:console|debugger|setTimeout|setInterval)\b|\$getWorkflowStaticData|getWorkflowStaticData|\$execution|\$workflow',
    'obfuscation_indicators': r'\b(?:atob|fromCharCode|decodeURIComponent)\s*\(|Buffer\s*\.\s*from\s*\(',
    'computed_string_member': r'''\[\s*["'`]''',
}


def bracket_contexts(code):
    """Narrow non-executing lexical evidence; not a JavaScript safety parser."""
    tokens, i = [], 0
    length = len(code)
    while i < length:
        start = i
        if code[i].isspace():
            i += 1
            continue
        if code.startswith('//', i):
            end = code.find('\n', i)
            i = length if end < 0 else end + 1
            continue
        if code.startswith('/*', i):
            end = code.find('*/', i + 2)
            if end < 0:
                return [{'classification': 'unresolved_lexical_context'}]
            i = end + 2
            continue
        if code[i] in '\"\'`':
            quote = code[i]
            i += 1
            while i < length:
                if code[i] == '\\':
                    i += 2
                elif code[i] == quote:
                    i += 1
                    break
                else:
                    i += 1
            else:
                return [{'classification': 'unresolved_lexical_context'}]
            # Template interpolation is intentionally opaque, never classified safe.
            tokens.append(('opaque_template' if quote == '`' else 'string', '', start, i))
            continue
        previous = tokens[-1][1] if tokens else None
        if code[i] == '/' and previous in (None, '=', '(', ',', '[', '{', ':', 'return', '!', '?', ';'):
            i += 1
            char_class = False
            while i < length:
                if code[i] == '\\':
                    i += 2
                    continue
                if code[i] == '[':
                    char_class = True
                elif code[i] == ']':
                    char_class = False
                elif code[i] == '/' and not char_class:
                    i += 1
                    while i < length and code[i].isalpha():
                        i += 1
                    break
                i += 1
            else:
                return [{'classification': 'unresolved_lexical_context'}]
            tokens.append(('regex', '', start, i))
            continue
        word = re.match(r'[A-Za-z_$][A-Za-z0-9_$]*', code[i:])
        if word:
            i += len(word.group())
            tokens.append(('word', word.group(), start, i))
        else:
            i += 1
            tokens.append(('punctuation', code[start:i], start, i))
    result = []
    for match in re.finditer(CAPABILITY_PATTERNS['computed_string_member'], code):
        index = next((j for j, token in enumerate(tokens) if token[2] == match.start()), None)
        classification = 'unresolved_or_opaque_context'
        span_end = match.end()
        if index is not None and tokens[index][1] == '[':
            previous = tokens[index - 1][1] if index else None
            before_previous = tokens[index - 2][1] if index > 1 else None
            if previous == 'return' and before_previous not in ('.', '?'):
                depth = 0
                for token in tokens[index:]:
                    if token[1] == '[':
                        depth += 1
                    elif token[1] == ']':
                        depth -= 1
                        if depth == 0:
                            classification = 'return_array_literal_not_member_access'
                            span_end = token[3]
                            break
            elif previous == '$json':
                classification = 'direct_input_property_pattern_requires_content_review'
        result.append({'classification': classification, 'start_offset': match.start(),
                       'end_offset': span_end, 'source_span_sha256': digest(code[match.start():span_end].encode()),
                       'security_clearance': False})
    return result


def scheduler_reference_trace(record):
    text = encoded({'parameters': [node.get('parameters', {}) for node in record.get('nodes', [])
                                   if isinstance(node, dict)],
                    'settings': record.get('settings', {})}).decode()
    return {'parameter_settings_text_mentions': {key: text.count(key) for key in
                      ('recurrenceRules', 'recurrenceRuleSignatures')},
            'explicit_state_access_indicator': bool(re.search(r'getWorkflowStaticData|\$workflow\s*\.\s*staticData', text)),
            'node_internal_implementation_available': False,
            'schedule_generation_effect_established': False,
            'deduplication_effect_established': False,
            'reminder_dispatch_effect_established': False,
            'restart_effect_established': False,
            'published_behavior_established': False}


def version_source_inventory(toc):
    """Archive TOC metadata only: a DATA entry is not proof of a matching row."""
    allowed = {'workflow_entity', 'workflow_history', 'workflow_published_version', 'workflow_publish_history'}
    found = {}
    for line in toc.splitlines():
        match = re.match(r'^\d+;\s+\d+\s+\d+\s+(TABLE DATA|TABLE)\s+(\S+)\s+(\S+)\s+', line)
        if match and match.group(3) in allowed:
            key = (match.group(2), match.group(3))
            found.setdefault(key, set()).add(match.group(1))
    return [{'schema': schema, 'table': table, 'schema_entry_present': 'TABLE' in kinds,
             'data_entry_present': 'TABLE DATA' in kinds,
             'matching_version_row_established': False, 'version_body_established': False}
            for (schema, table), kinds in sorted(found.items())]


def preserve_code_v2_for_review(node):
    """Copy for private inspection only. This does NOT enable the converter."""
    if (not isinstance(node, dict) or set(node) - NODE_FIELDS
            or node.get('type') != 'n8n-nodes-base.code'
            or type(node.get('typeVersion')) not in (int, float) or node['typeVersion'] != 2
            or not isinstance(node.get('id'), str) or not node['id']
            or not isinstance(node.get('name'), str)
            or not isinstance(node.get('parameters'), dict)
            or set(node['parameters']) != {'jsCode'}
            or not isinstance(node['parameters']['jsCode'], str)
            or not node['parameters']['jsCode'].strip()
            or 'credentials' in node):
        raise Rejected('UNREVIEWED_CODE_V2_STRUCTURE')
    return copy.deepcopy(node)


def inspect_code_v2(node):
    original = preserve_code_v2_for_review(node)
    code = original['parameters']['jsCode']
    signals = {category: bool(re.search(pattern, code)) for category, pattern in CAPABILITY_PATTERNS.items()}
    return {
        'node_id': original['id'], 'code_utf8_sha256': digest(code.encode('utf-8')),
        'type_version': 2, 'capability_indicators': signals,
        'bracket_context_evidence': bracket_contexts(code),
        'input_transform_indicators': bool(re.search(r'\$input|\$json|\$\(', code)),
        'time_dependency_indicators': bool(re.search(r'\bDate\b', code)),
        'assessment': 'flagged_for_private_review' if any(signals.values()) else 'no_flagged_capability_observed',
        'analysis_method': 'conservative_text_patterns_not_javascript_parser',
        'absence_of_capabilities_proven': False, 'execution_performed': False,
        'downstream_side_effects_possible': True,
        'byte_preserving_private_representation_possible': True,
        'conversion_approved': False,
    }


def runtime_state_inventory(record):
    """No guessed A/B classifications. Opaque runtime values remain unknown (C)."""
    inventory = []
    nodes = record.get('nodes', [])
    for field in ('staticData', 'pinData', 'executionData'):
        value = record.get(field)
        if value in (None, {}, [], ''):
            continue
        if not isinstance(value, dict):
            inventory.append({'path': [field], 'classification': 'C', 'owner_type': 'unknown',
                              'treatment': 'preserve_original_unchanged', 'reset_approved': False})
            continue
        for namespace, state in value.items():
            owner = next((node for node in nodes if isinstance(node, dict)
                          and namespace == 'node:' + str(node.get('name'))), None)
            owner_type = owner.get('type', 'unknown') if owner else 'unknown'
            leaves = state.items() if isinstance(state, dict) and state else [(None, state)]
            for key, item in leaves:
                path = [field, namespace] + ([key] if key is not None else [])
                inventory.append({'path': path, 'classification': 'C', 'owner_type': owner_type,
                                  'value_type': type(item).__name__,
                                  'treatment': 'preserve_original_unchanged',
                                  'reason': 'snapshot_does_not_establish_runtime_semantics',
                                  'reset_approved': False})
    return inventory


def require_resolved_runtime_state(record):
    if runtime_state_inventory(record):
        raise Rejected('UNKNOWN_RUNTIME_STATE_TREATMENT_NOT_APPROVED')


def version_provenance(record):
    current, published = record.get('versionId'), record.get('activeVersionId')
    if not isinstance(current, str) or not current:
        raise Rejected('INVALID_VERSION_METADATA')
    if published is not None and (not isinstance(published, str) or not published):
        raise Rejected('INVALID_VERSION_METADATA')
    if type(record.get('active')) is not bool:
        raise Rejected('INVALID_PUBLICATION_METADATA')
    if published and record['active'] is False:
        relation = 'contradictory_inactive_with_publication_reference'
    elif published:
        relation = 'matching_reference' if current == published else 'distinct_current_and_publication_reference'
    else:
        relation = 'active_without_publication_reference' if record['active'] else 'no_publication_reference'
    return {'current_version_id': current, 'published_reference_id': published,
            'original_active_flag': record['active'], 'relation': relation,
            'published_body_available': False, 'executing_version_established': False,
            'publication_history_established': False, 'identifiers_preserved_without_substitution': True}


def security_payload(raw):
    records = decode_json(raw)
    if not isinstance(records, list) or not records:
        raise Rejected('EXPECTED_WORKFLOW_SNAPSHOT_ARRAY')
    reviews = []
    ids = set()
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict) or not isinstance(record.get('nodes'), list):
            raise Rejected('INVALID_WORKFLOW_STRUCTURE')
        identity = record.get('id')
        if not isinstance(identity, str) or not identity or identity in ids:
            raise Rejected('INVALID_OR_DUPLICATE_WORKFLOW_ID')
        ids.add(identity)
        code = [inspect_code_v2(node) for node in record['nodes']
                if isinstance(node, dict) and node.get('type') == 'n8n-nodes-base.code']
        reviews.append({'source_index': index, 'workflow_id': identity, 'code_review': code,
                        'runtime_state': runtime_state_inventory(record),
                        'scheduler_reference_trace': scheduler_reference_trace(record),
                        'versions': version_provenance(record)})
    report = {'review_kind': 'private_nonexecuting_security_inventory', 'workflows': reviews,
              'workflow_count': len(records), 'code_node_count': sum(len(w['code_review']) for w in reviews),
              'source_sha256': digest(raw), 'state_transformation_approved': False,
              'conversion_approved': False, 'execution_performed': False,
              'source_promotion_approved': False, 'import_compatibility_verified': False}
    files = {'workflow-original.private.json': raw, 'security-review.private.json': encoded(report)}
    files['manifest.json'] = encoded({'kind': 'private_security_review_v2',
                                     'files_sha256': {name: digest(value) for name, value in files.items()},
                                     'execution_performed': False, 'state_modified': False})
    files['REVIEW_ONLY'] = b'PRIVATE_STATIC_REVIEW: no execution, state transformation or conversion approval.\n'
    return files, report


def validate_security_files(files):
    if 'workflow-original.private.json' not in files:
        raise Rejected('MISSING_PRIVATE_ORIGINAL')
    expected, report = security_payload(files['workflow-original.private.json'])
    if files != expected:
        raise Rejected('SECURITY_REVIEW_PROVENANCE_MISMATCH')
    return report
