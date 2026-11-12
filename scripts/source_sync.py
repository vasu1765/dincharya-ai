#!/usr/bin/env python3
"""Prepare private offline candidates. No service access or Git promotion."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

PROJECT = Path(__file__).resolve().parents[1]
MAX_BYTES = 32 * 1024 * 1024
MARKER = b'PRIVATE_CANDIDATE_ONLY: no Git promotion, import, execution, or deployment approval.\n'
NODE_PARAMETERS = {
    'n8n-nodes-base.manualTrigger': {1: set()},
    'n8n-nodes-base.set': {3.4: {'mode', 'assignments', 'options', 'includeOtherFields', 'value'}},
    'n8n-nodes-base.postgres': {2.8: {'operation', 'query', 'options'}},
    'n8n-nodes-base.scheduleTrigger': {1.4: {'rule'}},
    'n8n-nodes-base.telegram': {1.2: {'text', 'chatId', 'additionalFields'}},
    '@n8n/n8n-nodes-langchain.chainLlm': {1.9: {'text', 'promptType', 'batching', 'messages'}},
    '@n8n/n8n-nodes-langchain.lmChatOllama': {1: {'model', 'options'}},
    'n8n-nodes-base.webhook': {2.2: {'httpMethod', 'path', 'options', 'responseMode'}},
    'n8n-nodes-base.respondToWebhook': {1.5: {'respondWith', 'responseBody', 'options'}},
    'n8n-nodes-base.if': {2.4: {'conditions', 'options'}},
    'n8n-nodes-base.switch': {3.5: {'rules', 'options', 'looseTypeValidation'}},
    # Extend only with version-specific fixtures and explicit field review.
}
NODE_FIELDS = {'id', 'name', 'type', 'typeVersion', 'position', 'parameters',
               'credentials', 'disabled', 'notes', 'notesInFlow', 'alwaysOutputData',
               'executeOnce', 'retryOnFail', 'maxTries', 'waitBetweenTries', 'onError', 'webhookId'}
RECORD_FIELDS = {'id', 'name', 'nodes', 'connections', 'settings', 'active',
                 'versionId', 'activeVersionId', 'versionMetadata', 'createdAt',
                 'updatedAt', 'description', 'tags', 'meta', 'pinData', 'staticData',
                 'triggerCount', 'isArchived', 'versionCounter', 'parentFolderId',
                 'nodeGroups', 'sourceWorkflowId'}
NODE_PARAMETERS['n8n-nodes-base.set'][3.5] = NODE_PARAMETERS['n8n-nodes-base.set'][3.4] - {'value'}
MANIFEST_FIELDS = {'format_version', 'candidate_only', 'promotion_approved',
                   'human_review_attested', 'state_verified', 'import_compatibility_verified',
                   'database_execution_performed', 'schema_sha256', 'workflow_input_sha256',
                   'workflow_source_sha256', 'provenance_sha256', 'workflow_count',
                   'input_format', 'declared_state'}


class Rejected(ValueError):
    """Messages are fixed safe categories, never interpolated input contents."""


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Invalid command arguments; use --help. Input values are not displayed.\n')


def digest(content):
    return hashlib.sha256(content).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Rejected('DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def decode_json(content):
    try:
        return json.loads(content, object_pairs_hook=unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(Rejected('NONFINITE_NUMBER')))
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise Rejected('INVALID_JSON') from None


def scan_text(text):
    patterns = [
        r'\b\d{6,12}:[A-Za-z0-9_-]{30,}\b',
        r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        r'\b(?:ghp_|github_pat_|sk-proj-|AKIA)[A-Za-z0-9_-]{16,}',
        r'(?i)\b(?:postgres(?:ql)?|https?)://[^\s/:]+:[^\s/@]+@',
        r'(?i)\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}',
        r'''(?i)\b(?:password|api[_-]?key|encryption[_-]?key|bot[_-]?token|secret)\b["']?\s*[=:]\s*["']?[^\s"',;]{4,}''',
        r'''(?i)\bPASSWORD\s+["'][^"']+["']''',
        r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b',
    ]
    if any(re.search(pattern, text) for pattern in patterns):
        raise Rejected('POTENTIAL_SECRET')


def credential_references(value):
    if not isinstance(value, dict):
        raise Rejected('INVALID_CREDENTIAL_REFERENCE')
    for kind, reference in value.items():
        if (not isinstance(kind, str) or not isinstance(reference, dict)
                or set(reference) != {'id', 'name'}
                or any(not isinstance(v, str) or not v.strip() for v in reference.values())):
            raise Rejected('INVALID_CREDENTIAL_REFERENCE')
        for item in reference.values():
            scan_text(item)


def scan_tree(value):
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r'[^a-z0-9]', '', key.lower())
            if re.search(r'(credential|password|secret|token|authorization|cookie|apikey|encryptionkey|pindata|executiondata|staticdata|header|queryparameter)', normalized):
                if child not in (None, {}, [], ''):
                    raise Rejected('SENSITIVE_FIELD')
            scan_tree(child)
    elif isinstance(value, list):
        for child in value:
            scan_tree(child)
    elif isinstance(value, str):
        scan_text(value)
        if re.search(r'(?i)^(?:authorization|x-api-key|cookie|set-cookie)$', value.strip()):
            raise Rejected('AUTHENTICATION_HEADER')
    elif isinstance(value, float) and not math.isfinite(value):
        raise Rejected('NONFINITE_NUMBER')


def sql_statements(text):
    """Conservative lexical framing, not a PostgreSQL parser or execution check."""
    framed = []
    index, length = 0, len(text)
    while index < length:
        if text.startswith('--', index):
            end = text.find('\n', index)
            index = length if end < 0 else end + 1
            framed.append(' ')
        elif text.startswith('/*', index):
            depth = 1
            index += 2
            while index < length and depth:
                if text.startswith('/*', index):
                    depth += 1
                    index += 2
                elif text.startswith('*/', index):
                    depth -= 1
                    index += 2
                else:
                    index += 1
            if depth:
                raise Rejected('UNTERMINATED_SQL_COMMENT')
            framed.append(' ')
        elif text[index] in "'\"":
            quote = text[index]
            escaped = quote == "'" and index > 0 and text[index - 1] in 'eE'
            index += 1
            while index < length:
                if escaped and text[index] == '\\':
                    index += 2
                elif text[index] == quote:
                    if index + 1 < length and text[index + 1] == quote:
                        index += 2
                    else:
                        index += 1
                        break
                else:
                    index += 1
            else:
                raise Rejected('UNTERMINATED_SQL_LITERAL')
            framed.append(' LITERAL ')
        elif text[index] == '$' and (match := re.match(r'\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$', text[index:])):
            tag = match.group()
            end = text.find(tag, index + len(tag))
            if end < 0:
                raise Rejected('UNTERMINATED_SQL_BODY')
            framed.append(' BODY ')
            index = end + len(tag)
        else:
            framed.append(text[index])
            index += 1
    framed_text = ''.join(framed)
    if framed_text.strip() and not framed_text.rstrip().endswith(';'):
        raise Rejected('INCOMPLETE_SQL_STATEMENT')
    return [statement.strip() for statement in framed_text.split(';') if statement.strip()]


def validate_schema(content):
    try:
        text = content.decode('utf-8')
    except UnicodeError:
        raise Rejected('INVALID_SCHEMA_ENCODING') from None
    if not text.strip() or '\x00' in text:
        raise Rejected('INVALID_SCHEMA')
    scan_text(text)
    # pg_dump 17 patch releases can emit restrict/unrestrict; no other psql commands.
    restrict = None
    sql_lines = []
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith('\\'):
            match = re.fullmatch(r'\s*\\(restrict|unrestrict) ([A-Za-z0-9]+)\s*', line)
            if not match:
                raise Rejected('UNSAFE_PSQL_DIRECTIVE')
            kind, tag = match.groups()
            if kind == 'restrict' and restrict is None:
                restrict = tag
            elif kind == 'unrestrict' and restrict == tag:
                restrict = None
            else:
                raise Rejected('AMBIGUOUS_PSQL_DIRECTIVE')
            sql_lines.append('\n')
        else:
            sql_lines.append(line)
    if restrict is not None:
        raise Rejected('UNPAIRED_PSQL_DIRECTIVE')
    statements = sql_statements(''.join(sql_lines))
    found_definition = False
    for statement in statements:
        if re.match(r'(?is)^(?:COPY|INSERT|UPDATE|DELETE|MERGE|DO|CALL|CREATE\s+(?:ROLE|USER|SERVER|FOREIGN)|ALTER\s+(?:ROLE|USER))\b', statement):
            raise Rejected('NON_SCHEMA_SQL')
        if not re.match(r'(?is)^(?:CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|FUNCTION|PROCEDURE|TYPE|SCHEMA|VIEW|SEQUENCE|INDEX|UNIQUE\s+INDEX|TRIGGER|POLICY|EXTENSION|DOMAIN|AGGREGATE|MATERIALIZED\s+VIEW)\b|ALTER\s+(?:TABLE|FUNCTION|PROCEDURE|TYPE|SCHEMA|VIEW|SEQUENCE|INDEX|DOMAIN|EXTENSION|MATERIALIZED\s+VIEW)\b|COMMENT\s+ON\b|GRANT\b|REVOKE\b|SET\b|SELECT\s+pg_catalog\.set_config\s*\()', statement):
            raise Rejected('UNSUPPORTED_SQL_STATEMENT')
        found_definition |= bool(re.match(r'(?i)^CREATE\b', statement))
    if not found_definition:
        raise Rejected('NO_SCHEMA_DEFINITIONS')
    return content


def read_fd(fd, private=False):
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES or before.st_nlink != 1:
        raise Rejected('UNSAFE_OR_OVERSIZED_FILE')
    if private and (before.st_uid != os.getuid() or stat.S_IMODE(before.st_mode) != 0o600):
        raise Rejected('UNSAFE_FILE_PERMISSIONS')
    with os.fdopen(os.dup(fd), 'rb') as stream:
        content = stream.read(MAX_BYTES + 1)
    after = os.fstat(fd)
    if len(content) > MAX_BYTES or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise Rejected('FILE_CHANGED_DURING_READ')
    return content


def read_input(path, suffix):
    path = Path(path)
    if path.suffix != suffix or path.name.startswith('.env'):
        raise Rejected('UNSUPPORTED_INPUT_PATH')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        return read_fd(fd)
    finally:
        os.close(fd)


def load_schema(path):
    return validate_schema(read_input(path, '.sql'))


def fields(value, allowed, required=()):
    if not isinstance(value, dict) or set(value) - set(allowed) or not set(required) <= set(value):
        raise Rejected('UNSUPPORTED_NESTED_STRUCTURE')


def condition_structure(value):
    fields(value, {'options', 'combinator', 'conditions'}, {'options', 'combinator', 'conditions'})
    fields(value['options'], {'version', 'leftValue', 'caseSensitive', 'typeValidation'})
    for key, item in value['options'].items():
        expected = {'version': int, 'leftValue': str, 'caseSensitive': bool, 'typeValidation': str}[key]
        if type(item) is not expected:
            raise Rejected('INVALID_CONDITION_OPTION')
    if value['combinator'] not in ('and', 'or') or not isinstance(value['conditions'], list):
        raise Rejected('INVALID_CONDITIONS')
    for condition in value['conditions']:
        fields(condition, {'id', 'operator', 'leftValue', 'rightValue'}, {'id', 'operator', 'leftValue', 'rightValue'})
        if not isinstance(condition['id'], str):
            raise Rejected('INVALID_CONDITION_ID')
        fields(condition['operator'], {'type', 'operation', 'singleValue'}, {'type', 'operation'})
        if any(not isinstance(condition['operator'][key], str) for key in ('type', 'operation')):
            raise Rejected('INVALID_CONDITION_OPERATOR')
        if 'singleValue' in condition['operator'] and type(condition['operator']['singleValue']) is not bool:
            raise Rejected('INVALID_CONDITION_OPERATOR')


def observed_parameters(kind, parameters):
    """Syntactic adapters only. Never evaluate queries, expressions or code."""
    string_fields = {
        'n8n-nodes-base.postgres': {'operation', 'query'},
        'n8n-nodes-base.telegram': {'text', 'chatId'},
        '@n8n/n8n-nodes-langchain.chainLlm': {'text', 'promptType'},
        '@n8n/n8n-nodes-langchain.lmChatOllama': {'model'},
        'n8n-nodes-base.webhook': {'httpMethod', 'path', 'responseMode'},
        'n8n-nodes-base.respondToWebhook': {'respondWith', 'responseBody'},
    }.get(kind, set())
    if any(not isinstance(parameters.get(key), str) for key in string_fields):
        raise Rejected('INVALID_NODE_PARAMETER_TYPE')
    if kind == 'n8n-nodes-base.postgres':
        fields(parameters.get('options'), {'queryReplacement'})
        if parameters['operation'] != 'executeQuery' or any(not isinstance(v, str) for v in parameters['options'].values()):
            raise Rejected('UNSUPPORTED_POSTGRES_OPERATION')
    elif kind in {'@n8n/n8n-nodes-langchain.lmChatOllama', 'n8n-nodes-base.webhook',
                  'n8n-nodes-base.respondToWebhook', 'n8n-nodes-base.if'}:
        if parameters.get('options') != {}:
            raise Rejected('UNSUPPORTED_NODE_OPTIONS')
    if kind == 'n8n-nodes-base.telegram' and parameters.get('additionalFields') != {}:
        raise Rejected('UNSUPPORTED_TELEGRAM_OPTIONS')
    if kind == '@n8n/n8n-nodes-langchain.chainLlm':
        if parameters.get('batching') != {}:
            raise Rejected('UNSUPPORTED_CHAIN_BATCHING')
        if 'messages' in parameters:
            fields(parameters['messages'], {'messageValues'}, {'messageValues'})
            messages = parameters['messages']['messageValues']
            if not isinstance(messages, list):
                raise Rejected('INVALID_CHAIN_MESSAGES')
            for message in messages:
                fields(message, {'message'}, {'message'})
                if not isinstance(message['message'], str):
                    raise Rejected('INVALID_CHAIN_MESSAGES')
    if kind == 'n8n-nodes-base.scheduleTrigger':
        fields(parameters.get('rule'), {'interval'}, {'interval'})
        intervals = parameters['rule']['interval']
        if not isinstance(intervals, list) or not intervals:
            raise Rejected('INVALID_SCHEDULE_INTERVAL')
        for interval in intervals:
            fields(interval, {'field', 'minutesInterval'}, {'field', 'minutesInterval'})
            if not isinstance(interval['field'], str) or type(interval['minutesInterval']) is not int or interval['minutesInterval'] < 1:
                raise Rejected('INVALID_SCHEDULE_INTERVAL')
    if kind == 'n8n-nodes-base.if':
        condition_structure(parameters.get('conditions'))
    if kind == 'n8n-nodes-base.switch':
        fields(parameters.get('rules'), {'values'}, {'values'})
        rules = parameters['rules']['values']
        fields(parameters.get('options'), {'fallbackOutput'})
        if ('fallbackOutput' in parameters['options'] and not isinstance(parameters['options']['fallbackOutput'], str)
                or type(parameters.get('looseTypeValidation')) is not bool or not isinstance(rules, list)):
            raise Rejected('INVALID_SWITCH_OPTIONS')
        for rule in rules:
            fields(rule, {'outputKey', 'conditions', 'renameOutput'}, {'outputKey', 'conditions', 'renameOutput'})
            if not isinstance(rule['outputKey'], str) or type(rule['renameOutput']) is not bool:
                raise Rejected('INVALID_SWITCH_RULE')
            condition_structure(rule['conditions'])


def convert_workflows(raw, input_format, state):
    if input_format not in {'raw', 'editor'} or state not in {'unknown', 'draft', 'published'}:
        raise Rejected('INVALID_PROVENANCE_DECLARATION')
    if input_format == 'raw' and state == 'published':
        raise Rejected('RAW_PUBLICATION_UNVERIFIABLE')
    data = decode_json(raw)
    records = data if isinstance(data, list) else [data]
    if not records:
        raise Rejected('NO_WORKFLOWS')
    candidates, metadata, ids = [], [], set()
    for record in records:
        if not isinstance(record, dict) or set(record) - RECORD_FIELDS:
            raise Rejected('UNKNOWN_WORKFLOW_FIELDS')
        identity = record.get('id')
        if not isinstance(identity, str) or not identity.strip() or identity in ids:
            raise Rejected('INVALID_OR_DUPLICATE_WORKFLOW_ID')
        ids.add(identity)
        if not isinstance(record.get('name'), str) or not record['name'].strip():
            raise Rejected('INVALID_WORKFLOW_NAME')
        for field in ('active', 'isArchived'):
            if field in record and type(record[field]) is not bool:
                raise Rejected('INVALID_PUBLICATION_METADATA')
        for field in ('versionId', 'activeVersionId', 'createdAt', 'updatedAt', 'description', 'parentFolderId', 'sourceWorkflowId'):
            if field in record and record[field] is not None and (not isinstance(record[field], str) or not record[field]):
                raise Rejected('INVALID_VERSION_METADATA')
        for field in ('versionCounter', 'triggerCount'):
            if field in record and (type(record[field]) is not int or record[field] < 0):
                raise Rejected('INVALID_VERSION_METADATA')
        meta = record.get('meta')
        if meta is not None:
            fields(meta, {'templateCredsSetupCompleted'})
            if any(type(v) is not bool for v in meta.values()):
                raise Rejected('UNREVIEWED_WORKFLOW_METADATA')
        if record.get('nodeGroups') not in (None, []):
            raise Rejected('UNREVIEWED_NODE_GROUPS')
        if record.get('staticData') not in (None, {}):
            raise Rejected('RUNTIME_STATE_REQUIRES_REVIEW')
        if record.get('tags') not in (None, []):
            raise Rejected('UNREVIEWED_WORKFLOW_TAGS')
        version_metadata = record.get('versionMetadata')
        if version_metadata is not None and (not isinstance(version_metadata, dict)
                or set(version_metadata) - {'name', 'description'}
                or any(not isinstance(v, str) for v in version_metadata.values())):
            raise Rejected('INVALID_VERSION_METADATA')
        if state == 'published' and (not record.get('versionId')
                or record.get('active') is not True
                or record.get('activeVersionId', record['versionId']) != record['versionId']):
            raise Rejected('CONTRADICTORY_PUBLICATION_METADATA')
        if record.get('active') is False and record.get('activeVersionId'):
            raise Rejected('CONTRADICTORY_PUBLICATION_METADATA')
        nodes, connections, settings = record.get('nodes'), record.get('connections'), record.get('settings', {})
        if not isinstance(nodes, list) or not nodes or not isinstance(connections, dict) or not isinstance(settings, dict):
            raise Rejected('INVALID_WORKFLOW_STRUCTURE')
        if any(isinstance(node, dict) and node.get('type') == 'n8n-nodes-base.code' for node in nodes):
            raise Rejected('EXECUTABLE_NODE_REQUIRES_REVIEW')
        if set(settings) - {'timezone', 'executionOrder', 'binaryMode', 'callerPolicy', 'timeSavedMode', 'availableInMCP'}:
            raise Rejected('UNSUPPORTED_WORKFLOW_SETTINGS')
        if ('timezone' in settings and not isinstance(settings['timezone'], str)
                or 'executionOrder' in settings and (not isinstance(settings['executionOrder'], str)
                                                      or settings['executionOrder'] not in {'v0', 'v1'})):
            raise Rejected('INVALID_WORKFLOW_SETTINGS')
        if any(key in settings and not isinstance(settings[key], str) for key in ('binaryMode', 'callerPolicy', 'timeSavedMode')):
            raise Rejected('INVALID_WORKFLOW_SETTINGS')
        if 'availableInMCP' in settings and type(settings['availableInMCP']) is not bool:
            raise Rejected('INVALID_WORKFLOW_SETTINGS')
        names, node_ids, references, candidate_nodes = set(), set(), {}, []
        for node in nodes:
            if not isinstance(node, dict) or set(node) - NODE_FIELDS:
                raise Rejected('UNKNOWN_NODE_FIELDS')
            name, node_id = node.get('name'), node.get('id')
            if (not isinstance(name, str) or not name.strip() or name in names
                    or not isinstance(node_id, str) or not node_id or node_id in node_ids):
                raise Rejected('INVALID_OR_DUPLICATE_NODE_IDENTITY')
            names.add(name)
            node_ids.add(node_id)
            kind, version = node.get('type'), node.get('typeVersion')
            if kind == 'n8n-nodes-base.code':
                raise Rejected('EXECUTABLE_NODE_REQUIRES_REVIEW')
            if (not isinstance(kind, str) or type(version) not in (int, float)
                    or type(version) is float and not math.isfinite(version)):
                raise Rejected('INVALID_NODE_VERSION')
            supported = NODE_PARAMETERS.get(kind, {}).get(version)
            if supported is None:
                raise Rejected('UNSUPPORTED_NODE_VERSION')
            parameters = node.get('parameters')
            if not isinstance(parameters, dict) or set(parameters) - supported:
                raise Rejected('UNSUPPORTED_NODE_PARAMETERS')
            observed_parameters(kind, parameters)
            if kind == 'n8n-nodes-base.set':
                if ('mode' in parameters and parameters['mode'] != 'manual'
                        or 'options' in parameters and parameters['options'] != {}
                        or 'includeOtherFields' in parameters and type(parameters['includeOtherFields']) is not bool):
                    raise Rejected('UNSUPPORTED_SET_OPTIONS')
                if 'assignments' in parameters:
                    assignments = parameters['assignments']
                    if not isinstance(assignments, dict) or set(assignments) != {'assignments'} or not isinstance(assignments['assignments'], list):
                        raise Rejected('INVALID_ASSIGNMENT_STRUCTURE')
                    for assignment in assignments['assignments']:
                        if (not isinstance(assignment, dict) or set(assignment) != {'id', 'name', 'value', 'type'}
                                or not isinstance(assignment['id'], str) or not assignment['id']
                                or not isinstance(assignment['name'], str) or not assignment['name']
                                or not isinstance(assignment['type'], str)
                                or assignment['type'] not in {'string', 'number', 'boolean', 'array', 'object'}):
                            raise Rejected('INVALID_ASSIGNMENT_STRUCTURE')
            position = node.get('position')
            if (not isinstance(position, list) or len(position) != 2
                    or any(type(v) not in (int, float) or abs(v) > 1_000_000_000
                           or type(v) is float and not math.isfinite(v) for v in position)):
                raise Rejected('INVALID_NODE_POSITION')
            for field in ('disabled', 'notesInFlow', 'alwaysOutputData', 'executeOnce', 'retryOnFail'):
                if field in node and type(node[field]) is not bool:
                    raise Rejected('INVALID_NODE_OPTION')
            for field in ('maxTries', 'waitBetweenTries'):
                if field in node and (type(node[field]) is not int or node[field] < 0):
                    raise Rejected('INVALID_NODE_OPTION')
            if 'notes' in node and not isinstance(node['notes'], str):
                raise Rejected('INVALID_NODE_OPTION')
            if 'webhookId' in node and (not isinstance(node['webhookId'], str) or not node['webhookId']):
                raise Rejected('INVALID_WEBHOOK_ID')
            if 'onError' in node and (not isinstance(node['onError'], str) or node['onError'] not in {'stopWorkflow', 'continueRegularOutput', 'continueErrorOutput'}):
                raise Rejected('INVALID_NODE_OPTION')
            candidate_node = copy.deepcopy(node)
            if 'credentials' in candidate_node:
                credential_references(candidate_node['credentials'])
                references[node_id] = candidate_node.pop('credentials')
            candidate_nodes.append(candidate_node)
        node_types = {node['name']: node['type'] for node in nodes}
        for origin, outputs in connections.items():
            if origin not in names or not isinstance(outputs, dict) or set(outputs) - {'main', 'ai_languageModel'}:
                raise Rejected('INVALID_CONNECTION_ORIGIN')
            for connection_type, branches in outputs.items():
                origin_node = next(node for node in nodes if node['name'] == origin)
                maximum = 2 if origin_node['type'] == 'n8n-nodes-base.if' else (
                    len(origin_node['parameters']['rules']['values']) + 1 if origin_node['type'] == 'n8n-nodes-base.switch' else 1)
                if (not isinstance(branches, list) or len(branches) > maximum
                        or connection_type == 'ai_languageModel' and origin_node['type'] != '@n8n/n8n-nodes-langchain.lmChatOllama'):
                    raise Rejected('INVALID_CONNECTION_BRANCHES')
                for branch in branches:
                    if not isinstance(branch, list):
                        raise Rejected('INVALID_CONNECTION_BRANCH')
                    for edge in branch:
                        if (not isinstance(edge, dict) or set(edge) != {'node', 'type', 'index'}
                                or not isinstance(edge.get('node'), str) or edge['node'] not in names
                                or edge.get('type') != connection_type or type(edge.get('index')) is not int or edge['index'] != 0
                                or connection_type == 'ai_languageModel' and node_types[edge['node']] != '@n8n/n8n-nodes-langchain.chainLlm'):
                            raise Rejected('INVALID_CONNECTION_TARGET')
        scan_record = copy.deepcopy(record)
        for node in scan_record['nodes']:
            node.pop('credentials', None)
        scan_tree(scan_record)
        candidate = {'name': record['name'], 'nodes': candidate_nodes,
                     'connections': copy.deepcopy(connections), 'settings': copy.deepcopy(settings), 'active': False}
        candidates.append(candidate)
        metadata.append({'original_record': record, 'credential_references': references,
                         'input_format': input_format, 'declared_state': state,
                         'state_verified': False, 'import_compatibility_verified': False})
    return candidates, metadata


def load_workflows(path, input_format, state):
    raw = read_input(path, '.json')
    candidates, metadata = convert_workflows(raw, input_format, state)
    return candidates, metadata, digest(raw)


def private_root_fd(path):
    path = Path(os.path.abspath(path))
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise Rejected('SYMLINK_PATH')
        if parent == PROJECT or PROJECT in parent.parents:
            raise Rejected('PRIVATE_ROOT_INSIDE_PROJECT')
        if ((parent / '.git').is_file() or (parent / '.git/HEAD').is_file()
                or (parent / 'HEAD').is_file() and (parent / 'objects').is_dir() and (parent / 'refs').is_dir()):
            raise Rejected('PRIVATE_ROOT_INSIDE_GIT')
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    info = os.fstat(fd)
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        os.close(fd)
        raise Rejected('PRIVATE_ROOT_PERMISSIONS')
    return path, fd


def child_name(root, path):
    path = Path(os.path.abspath(path))
    if path.parent != root or path.name in {'', '.', '..'}:
        raise Rejected('OUTPUT_OUTSIDE_PRIVATE_ROOT')
    return path.name


def open_child(root_fd, name, create=False):
    if create:
        try:
            os.mkdir(name, mode=0o700, dir_fd=root_fd)
        except FileExistsError:
            raise Rejected('OUTPUT_ALREADY_EXISTS') from None
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
    info = os.fstat(fd)
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        os.close(fd)
        raise Rejected('DIRECTORY_PERMISSIONS')
    return fd


def write_file(directory_fd, name, content):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def prepare(schema, workflow, output, private_output, input_format, state, reviewed, private_root):
    if reviewed is not True:
        raise Rejected('REVIEW_ATTESTATION_REQUIRED')
    root, root_fd = private_root_fd(private_root)
    output_fd = metadata_fd = None
    try:
        output_name, metadata_name = child_name(root, output), child_name(root, private_output)
        if output_name == metadata_name:
            raise Rejected('OUTPUTS_MUST_BE_DISJOINT')
        # Read only explicitly supplied inputs, exactly once. No output before validation.
        schema_bytes, raw = load_schema(schema), read_input(workflow, '.json')
        candidates, metadata = convert_workflows(raw, input_format, state)
        candidate_bytes, metadata_bytes = encoded(candidates), encoded(metadata)
        manifest = {'format_version': 2, 'candidate_only': True, 'promotion_approved': False,
                    'human_review_attested': True, 'state_verified': False,
                    'import_compatibility_verified': False, 'database_execution_performed': False,
                    'schema_sha256': digest(schema_bytes), 'workflow_input_sha256': digest(raw),
                    'workflow_source_sha256': digest(candidate_bytes), 'provenance_sha256': digest(metadata_bytes),
                    'workflow_count': len(candidates), 'input_format': input_format, 'declared_state': state}
        # mkdir/O_EXCL and dir-relative no-follow writes prevent replacing existing paths.
        metadata_fd = open_child(root_fd, metadata_name, create=True)
        output_fd = open_child(root_fd, output_name, create=True)
        write_file(metadata_fd, 'workflow-input.private.json', raw)
        write_file(metadata_fd, 'workflow-provenance.private.json', metadata_bytes)
        write_file(output_fd, 'application-schema.sql', schema_bytes)
        write_file(output_fd, 'workflows.candidate.json', candidate_bytes)
        write_file(output_fd, 'manifest.json', encoded(manifest))
        write_file(output_fd, 'PREPARED', MARKER)
        return manifest
    finally:
        for fd in (output_fd, metadata_fd, root_fd):
            if fd is not None:
                os.close(fd)


def read_directory(fd, expected):
    if set(os.listdir(fd)) != set(expected):
        raise Rejected('UNEXPECTED_OR_MISSING_BUNDLE_FILES')
    result = {}
    for name in sorted(expected):
        file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            result[name] = read_fd(file_fd, private=True)
        finally:
            os.close(file_fd)
    return result


WORKFLOW_MARKER = b'PRIVATE_WORKFLOW_REVIEW_ONLY: no import, execution or Git promotion approval.\n'


def workflow_snapshot_payload(raw, report_raw, source_path):
    """Keep every original byte; convert independent records or record rejection."""
    report = decode_json(report_raw)
    if not isinstance(report, dict) or not isinstance(report.get('inputs'), list):
        raise Rejected('INVALID_PRIOR_INTEGRITY_REPORT')
    entries = [entry for entry in report['inputs'] if isinstance(entry, dict)
               and entry.get('source_path') == source_path]
    if (len(entries) != 1 or entries[0].get('checksum_verified') is not True
            or entries[0].get('sha256') != digest(raw)):
        raise Rejected('PRIOR_VERIFIED_INPUT_MISMATCH')
    records = decode_json(raw)
    if not isinstance(records, list) or not records:
        raise Rejected('EXPECTED_WORKFLOW_SNAPSHOT_ARRAY')
    candidates, provenance, rejected = [], [], []
    identities = [record.get('id') for record in records if isinstance(record, dict)]
    if any(not isinstance(identity, str) for identity in identities) or len(set(identities)) != len(identities):
        raise Rejected('INVALID_OR_DUPLICATE_WORKFLOW_ID')
    for index, record in enumerate(records, 1):
        try:
            converted, metadata = convert_workflows(encoded([record]), 'raw', 'unknown')
        except Rejected as error:
            rejected.append({'source_index': index, 'category': str(error)})
        else:
            candidates.extend(converted)
            provenance.append({'source_index': index, **metadata[0]})
    files = {'workflow-input.private.json': raw, 'integrity-report.private.json': report_raw,
             'workflows.candidate.json': encoded(candidates),
             'workflow-provenance.private.json': encoded(provenance),
             'rejections.private.json': encoded(rejected)}
    manifest = {'format_version': 1, 'kind': 'private-workflow-snapshot-review',
                'source_path': source_path, 'input_format': 'raw', 'declared_state': 'unknown',
                'state_verified': False, 'human_review_attested': False,
                'promotion_approved': False, 'import_compatibility_verified': False,
                'execution_performed': False, 'workflow_count': len(records),
                'converted_count': len(candidates), 'rejected_count': len(rejected),
                'files_sha256': {name: digest(value) for name, value in files.items()}}
    files['manifest.json'] = encoded(manifest)
    files['REVIEW_ONLY'] = WORKFLOW_MARKER
    return files, manifest


def prepare_workflow_snapshot(snapshot, integrity_report, output, private_root):
    root, root_fd = private_root_fd(private_root)
    output_fd = None
    try:
        name = child_name(root, output)
        raw, report = read_input(snapshot, '.json'), read_input(integrity_report, '.json')
        files, manifest = workflow_snapshot_payload(raw, report, str(Path(snapshot).absolute()))
        output_fd = open_child(root_fd, name, create=True)
        for filename, content in files.items():
            write_file(output_fd, filename, content)
        return manifest
    finally:
        for fd in (output_fd, root_fd):
            if fd is not None:
                os.close(fd)


def validate_workflow_snapshot(output, private_root):
    root, root_fd = private_root_fd(private_root)
    output_fd = None
    try:
        output_fd = open_child(root_fd, child_name(root, output))
        files = read_directory(output_fd, {'workflow-input.private.json', 'integrity-report.private.json',
                  'workflows.candidate.json', 'workflow-provenance.private.json',
                  'rejections.private.json', 'manifest.json', 'REVIEW_ONLY'})
        manifest = decode_json(files['manifest.json'])
        if not isinstance(manifest, dict) or not isinstance(manifest.get('source_path'), str):
            raise Rejected('INVALID_MANIFEST_FIELDS')
        expected, result = workflow_snapshot_payload(files['workflow-input.private.json'],
                      files['integrity-report.private.json'], manifest['source_path'])
        if files != expected:
            raise Rejected('INTEGRITY_OR_PROVENANCE_MISMATCH')
        return result
    finally:
        for fd in (output_fd, root_fd):
            if fd is not None:
                os.close(fd)


def validate_bundle(directory, private_output, private_root):
    root, root_fd = private_root_fd(private_root)
    candidate_fd = metadata_fd = None
    try:
        candidate_name, metadata_name = child_name(root, directory), child_name(root, private_output)
        if candidate_name == metadata_name:
            raise Rejected('OUTPUTS_MUST_BE_DISJOINT')
        candidate_fd = open_child(root_fd, candidate_name)
        metadata_fd = open_child(root_fd, metadata_name)
        # Each artifact read once. Parse/hash/compare the same immutable bytes.
        files = read_directory(candidate_fd, {'application-schema.sql', 'workflows.candidate.json', 'manifest.json', 'PREPARED'})
        private = read_directory(metadata_fd, {'workflow-input.private.json', 'workflow-provenance.private.json'})
        manifest = decode_json(files['manifest.json'])
        if not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS:
            raise Rejected('INVALID_MANIFEST_FIELDS')
        constants = {'format_version': 2, 'candidate_only': True, 'promotion_approved': False,
                     'human_review_attested': True, 'state_verified': False,
                     'import_compatibility_verified': False, 'database_execution_performed': False}
        if any(type(manifest[k]) is not type(v) or manifest[k] != v for k, v in constants.items()):
            raise Rejected('INVALID_MANIFEST_FLAGS')
        if type(manifest['workflow_count']) is not int or manifest['workflow_count'] < 1:
            raise Rejected('INVALID_WORKFLOW_COUNT')
        for key in ('schema_sha256', 'workflow_input_sha256', 'workflow_source_sha256', 'provenance_sha256'):
            if not isinstance(manifest[key], str) or not re.fullmatch('[0-9a-f]{64}', manifest[key]):
                raise Rejected('INVALID_DIGEST')
        validate_schema(files['application-schema.sql'])
        candidates, metadata = convert_workflows(private['workflow-input.private.json'], manifest['input_format'], manifest['declared_state'])
        if (files['PREPARED'] != MARKER
                or files['workflows.candidate.json'] != encoded(candidates)
                or private['workflow-provenance.private.json'] != encoded(metadata)
                or manifest['workflow_count'] != len(candidates)
                or digest(files['application-schema.sql']) != manifest['schema_sha256']
                or digest(files['workflows.candidate.json']) != manifest['workflow_source_sha256']
                or digest(private['workflow-input.private.json']) != manifest['workflow_input_sha256']
                or digest(private['workflow-provenance.private.json']) != manifest['provenance_sha256']):
            raise Rejected('INTEGRITY_OR_PROVENANCE_MISMATCH')
    finally:
        for fd in (candidate_fd, metadata_fd, root_fd):
            if fd is not None:
                os.close(fd)


def report_error(error):
    # Only Rejected has deliberately safe fixed messages; never echo OS/parser errors.
    category = str(error) if isinstance(error, Rejected) else 'IO_OR_INPUT_ERROR'
    print(f'Offline operation rejected: {category}. No promotion or deployment occurred.', file=sys.stderr)


def main():
    parser = SafeArgumentParser(description=__doc__)
    for name in ('schema', 'workflow', 'output', 'private-output', 'private-root'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--input-format', choices=['raw', 'editor'], required=True)
    parser.add_argument('--state', choices=['draft', 'published', 'unknown'], default='unknown')
    parser.add_argument('--reviewed-inputs', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepare(args.schema, args.workflow, args.output, args.private_output,
                args.input_format, args.state, args.reviewed_inputs, args.private_root)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError) as error:
        report_error(error)
        return 1
    print('Private offline candidate prepared. Git promotion and import compatibility are NOT approved.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
