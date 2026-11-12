"""Read verified installed source as text; never imports/evaluates JavaScript."""
import io
from pathlib import Path, PurePosixPath
import re
import tarfile
from source_sync import Rejected, read_input, digest, decode_json
from workflow_security import runtime_state_inventory

PREFIX = 'node_modules/n8n-nodes-base/dist/nodes/Schedule/'
REQUIRED_FILES = {'package.json', 'node_modules/n8n-nodes-base/package.json',
                  PREFIX + 'ScheduleTrigger.node.js', PREFIX + 'GenericFunctions.js'}
ANCHORS = {
    'node_scoped_engine_state': ('ScheduleTrigger.node.js', "this.getWorkflowStaticData('node')"),
    'recurrence_filter_before_emit': ('ScheduleTrigger.node.js', 'recurrenceCheck)(recurrence, staticData.recurrenceRules, timezone)'),
    'scheduled_setup_rearms_state': ('ScheduleTrigger.node.js', 'resetStaleRecurrence)(staticData, rules)'),
    'cron_registration': ('ScheduleTrigger.node.js', 'this.helpers.registerCron(cron,'),
    'separate_scheduled_time_dedup_key': ('ScheduleTrigger.node.js', '${workflowId}:${nodeId}:${scheduledTime.toISOString()}'),
    'manual_bypasses_recurrence': ('ScheduleTrigger.node.js', 'executeTrigger(recurrence, true)'),
    'last_execution_read': ('GenericFunctions.js', 'recurrenceRules[index] ?? undefined'),
    'last_execution_write': ('GenericFunctions.js', 'recurrenceRules[index] = absoluteMinute'),
    'config_signature_comparison': ('GenericFunctions.js', 'storedSignature === signature'),
    'stale_state_rearm': ('GenericFunctions.js', 'staticData.recurrenceRules[index] = undefined'),
    'signature_update': ('GenericFunctions.js', 'staticData.recurrenceRuleSignatures[index] = signature'),
    'state_trimmed_to_rule_count': ('GenericFunctions.js', 'staticData.recurrenceRules.length = rules.length'),
}


def inspect_source_files(files):
    if not REQUIRED_FILES <= set(files):
        raise Rejected('MISSING_RELEVANT_SCHEDULER_SOURCE')
    package = decode_json(files['package.json'])
    base = decode_json(files['node_modules/n8n-nodes-base/package.json'])
    if package.get('name') != 'n8n' or package.get('version') != '2.47.3' or base.get('name') != 'n8n-nodes-base' or base.get('version') != '2.47.2':
        raise Rejected('UNREVIEWED_PACKAGE_VERSION_MAPPING')
    locations = {}
    for fact, (filename, anchor) in ANCHORS.items():
        path = PREFIX + filename
        lines = files[path].decode('utf-8').splitlines()
        found = [index + 1 for index, line in enumerate(lines) if anchor in line]
        if not found:
            raise Rejected('UNREVIEWED_SCHEDULER_IMPLEMENTATION')
        locations[fact] = {'source_path': path, 'lines': found, 'source_sha256': digest(files[path])}
    return {'n8n_version': '2.47.3', 'node_package_version': '2.47.2',
            'source_facts': locations, 'source_files_sha256': {name: digest(files[name]) for name in sorted(REQUIRED_FILES)},
            'assessment_scope': 'reviewed_exported_image_only_not_historical_runtime_proof',
            'analysis_method': 'static_source_review_with_hash_and_line_anchors_not_execution',
            'native_scheduler_state_established': True, 'execution_performed': False,
            'import_api_contract_verified': False, 'persistence_flush_contract_verified': False,
            'historical_runtime_compatibility_established': False, 'reset_approved': False}


def read_verified_source_export(root):
    root = Path(root)
    marker = read_input(root / 'EXPORTED', '')
    if not marker.startswith(b'STATIC_SOURCE_EXPORTED:'):
        raise Rejected('MISSING_SOURCE_EXPORT_MARKER')
    required = {'scheduler-source.tar', 'image-id.private.txt', 'verified-version.private.txt'}
    checksums = {}
    for line in read_input(root / 'SHA256SUMS', '').decode().splitlines():
        match = re.fullmatch(r'([0-9a-f]{64}) ([ *])(.+)', line)
        if not match or match.group(3) not in required or match.group(3) in checksums:
            raise Rejected('UNEXPECTED_SOURCE_MANIFEST')
        checksums[match.group(3)] = match.group(1)
    if set(checksums) != required:
        raise Rejected('INCOMPLETE_SOURCE_MANIFEST')
    originals = {}
    for name, checksum in checksums.items():
        content = read_input(root / name, Path(name).suffix)
        if digest(content) != checksum:
            raise Rejected('SOURCE_EXPORT_CHECKSUM_MISMATCH')
        originals[name] = content
    if not re.fullmatch(r'sha256:6723b440354b[0-9a-f]{52}\n?', originals['image-id.private.txt'].decode()):
        raise Rejected('SOURCE_IMAGE_ID_MISMATCH')
    if not originals['verified-version.private.txt'].startswith(b'2.47.3 '):
        raise Rejected('SOURCE_RELEASE_ATTESTATION_MISMATCH')
    files, seen, total = {}, set(), 0
    try:
        with tarfile.open(fileobj=io.BytesIO(originals['scheduler-source.tar']), mode='r:') as archive:
            for member in archive:
                path = PurePosixPath(member.name)
                name = path.as_posix()
                if (path.is_absolute() or '..' in path.parts or name in seen
                        or not (member.isdir() or member.isfile())
                        or name not in {'package.json', 'node_modules/n8n-nodes-base/package.json', PREFIX.rstrip('/')}
                        and not name.startswith(PREFIX)):
                    raise Rejected('UNSAFE_SOURCE_ARCHIVE_MEMBER')
                seen.add(name)
                if member.isfile():
                    total += member.size
                    if total > 64 * 1024 * 1024:
                        raise Rejected('OVERSIZED_SOURCE_ARCHIVE')
                    # No extraction onto the filesystem, path following or code loading.
                    files[name] = archive.extractfile(member).read()
    except tarfile.TarError:
        raise Rejected('INVALID_SOURCE_ARCHIVE') from None
    evidence = inspect_source_files(files)
    evidence.update(checksums_verified=True, export_manifest=checksums,
                    image_id=originals['image-id.private.txt'].decode().strip())
    return originals, evidence


def assess_scheduler_state(record, evidence):
    if not isinstance(record, dict) or not isinstance(evidence, dict):
        raise Rejected('INVALID_STATE_ASSESSMENT_INPUT')
    if (evidence.get('checksums_verified') is not True
            or evidence.get('native_scheduler_state_established') is not True
            or evidence.get('n8n_version') != '2.47.3'
            or evidence.get('node_package_version') != '2.47.2'
            or set(evidence.get('source_facts', {})) != set(ANCHORS)):
        raise Rejected('VERIFIED_SOURCE_EVIDENCE_REQUIRED')
    result = runtime_state_inventory(record)
    for item in result:
        path = item['path']
        owner = next((node for node in record.get('nodes', []) if isinstance(node, dict)
                      and len(path) == 3 and path[1] == 'node:' + str(node.get('name'))), None)
        if (path[0] == 'staticData' and len(path) == 3
                and owner and owner.get('type') == 'n8n-nodes-base.scheduleTrigger'
                and type(owner.get('typeVersion')) in (int, float) and owner['typeVersion'] == 1.4
                and path[2] in {'recurrenceRules', 'recurrenceRuleSignatures'}):
            value = record['staticData'][path[1]][path[2]]
            if not isinstance(value, list):
                continue
            item.update(classification='B', reason='native_engine_recurrence_filter_or_config_signature_state',
                        classification_scope='verified_exported_image_only', application_specific=False,
                        reset_approved=False, import_treatment_approved=False,
                        treatment='preserve_original_unchanged')
    return result
