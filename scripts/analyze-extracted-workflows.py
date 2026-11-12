#!/usr/bin/env python3
"""Read only approved extracted SQL/private proof; never runs SQL, JS or Docker."""
import os
from pathlib import Path
import re
import sys
from source_sync import (SafeArgumentParser, Rejected, read_input, digest, encoded,
                         private_root_fd, child_name, open_child, write_file,
                         read_directory, validate_workflow_snapshot, report_error)
from version_evidence import plan_authorized_toc
from extracted_workflows import analyze_versions

CHECKED_FILES = {'authorized.list', 'fresh-toc.private.txt', 'client-image.private.txt',
                 'client-version.private.txt', 'authorized-tables.sql'}


def verify_extraction(path, expected_ids):
    path = Path(path)
    marker = read_input(path / 'EXTRACTED', '')
    if not marker.startswith(b'EXTRACTION_COMPLETED: selected SQL only; never executed or restored.'):
        raise Rejected('INVALID_EXTRACTION_COMPLETION_MARKER')
    manifest = read_input(path / 'SHA256SUMS', '')
    expected = {}
    for line in manifest.decode().splitlines():
        match = re.fullmatch(r'([0-9a-f]{64}) ([ *])(.+)', line)
        if not match or match.group(3) not in CHECKED_FILES or match.group(3) in expected:
            raise Rejected('UNEXPECTED_EXTRACTION_CHECKSUM_ENTRY')
        expected[match.group(3)] = match.group(1)
    if set(expected) != CHECKED_FILES:
        raise Rejected('MISSING_EXTRACTION_CHECKSUM_ENTRY')
    originals = {}
    for name, checksum in expected.items():
        content = read_input(path / name, Path(name).suffix)
        if digest(content) != checksum:
            raise Rejected('EXTRACTION_CHECKSUM_MISMATCH')
        originals[name] = content
    selected = plan_authorized_toc(originals['authorized.list'].decode())
    fresh = plan_authorized_toc(originals['fresh-toc.private.txt'].decode())
    lines = originals['authorized.list'].decode().splitlines()
    if len(lines) != 6 or {entry['entry_id'] for entry in selected} != set(expected_ids) or selected != fresh:
        raise Rejected('UNEXPECTED_AUTHORIZED_SELECTION')
    if not re.fullmatch(r'pg_restore \(PostgreSQL\) 17\.11[^\n]*\n?', originals['client-version.private.txt'].decode()):
        raise Rejected('UNEXPECTED_EXTRACTION_CLIENT_VERSION')
    archive = read_input(path / 'archive-sha256.private.txt', '.txt').decode().strip()
    if not re.fullmatch('[0-9a-f]{64}', archive):
        raise Rejected('INVALID_EVIDENCE_DIGEST')
    return originals['authorized-tables.sql'], archive, {
        'source_directory': str(path.absolute()), 'verified_checksums': expected,
        'completion_marker_sha256': digest(marker), 'checksum_manifest_sha256': digest(manifest),
        'archive_sha256': archive, 'selected_entries': selected,
        'integrity_is_unsigned_not_authentication': True}


def analysis_files(snapshot_raw, sql_raw, archive_hash, proof):
    result = analyze_versions(snapshot_raw, sql_raw, archive_hash)
    files = {
        'current-snapshot.original.private.json': snapshot_raw,
        'extracted-tables.original.private.sql': sql_raw,
        'parsed-tables.private.json': encoded(result['tables']),
        'version-resolutions.private.json': encoded(result['resolutions']),
        'published-bodies.private.json': encoded(result['published_bodies']),
        'current-candidates.private.json': encoded(result['current_candidates']),
        'current-provenance.private.json': encoded(result['current_provenance']),
        'rejected-current.private.json': encoded(result['rejections']),
        'unversioned-events.private.json': encoded(result['unversioned_events']),
        'event-version-references.private.json': encoded(result['event_references']),
        'extraction-provenance.private.json': encoded(proof),
    }
    files['manifest.json'] = encoded({'kind': 'private_extracted_workflow_analysis_v2',
        'comparison_policy': 'JSON_object_key_order_ignored_arrays_scalar_types_and_code_text_preserved',
        'files_sha256': {key: digest(value) for key, value in files.items()},
        'relevant_history_count': result['relevant_history_count'],
        'current_candidate_count': len(result['current_candidates']),
        'published_body_count': len(result['published_bodies']),
        'complete_published_candidate_count': 0,
        'published_settings_available': False, 'published_runtime_state_available': False,
        'sql_executed': False, 'code_executed': False, 'state_modified': False,
        'source_promotion_approved': False, 'historical_runtime_version_established': False})
    files['REVIEW_ONLY'] = b'Private version evidence only; no SQL/Code execution, imports, state changes or promotion.\n'
    return files, result


def validate_analysis_files(files):
    keys = ('current-snapshot.original.private.json', 'extracted-tables.original.private.sql', 'extraction-provenance.private.json')
    if not all(key in files for key in keys):
        raise Rejected('MISSING_ANALYSIS_ORIGINALS')
    from source_sync import decode_json
    proof = decode_json(files[keys[2]])
    expected, result = analysis_files(files[keys[0]], files[keys[1]], proof['archive_sha256'], proof)
    if expected != files:
        raise Rejected('ANALYSIS_PROVENANCE_MISMATCH')
    return result


def main():
    parser = SafeArgumentParser(description=__doc__)
    for name in ('extraction-dir', 'snapshot', 'prior-review', 'prior-root', 'private-root', 'output', 'expected-ids'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    rfd = ofd = None
    try:
        expected_ids = [int(value) for value in args.expected_ids.split(',')]
        if len(expected_ids) != 6 or len(set(expected_ids)) != 6:
            raise Rejected('EXPECTED_SIX_UNIQUE_TOC_IDENTIFIERS')
        sql, archive_hash, proof = verify_extraction(args.extraction_dir, expected_ids)
        prior = validate_workflow_snapshot(args.prior_review, args.prior_root)
        raw = read_input(args.snapshot, '.json')
        if prior['source_path'] != str(Path(args.snapshot).absolute()) or prior['files_sha256']['workflow-input.private.json'] != digest(raw):
            raise Rejected('PRIOR_VERIFIED_INPUT_MISMATCH')
        files, result = analysis_files(raw, sql, archive_hash, proof)
        root, rfd = private_root_fd(args.private_root)
        ofd = open_child(rfd, child_name(root, args.output), create=True)
        for name, content in files.items():
            write_file(ofd, name, content)
        validate_analysis_files(read_directory(ofd, set(files)))
        print('Private analysis validated: historical versions=' + str(result['relevant_history_count'])
              + ', published bodies=' + str(len(result['published_bodies']))
              + ', current structural candidates=' + str(len(result['current_candidates'])) + '.')
        print('Published settings/runtime state unavailable. No execution, import, state change or source promotion.')
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError) as error:
        report_error(error)
        return 1
    finally:
        for fd in (ofd, rfd):
            if fd is not None:
                os.close(fd)
    return 0


if __name__ == '__main__':
    sys.exit(main())
