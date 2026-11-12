#!/usr/bin/env python3
"""Private installed-source review; never executes JS or mutates workflow state."""
import os
from pathlib import Path
import sys
from source_sync import (SafeArgumentParser, Rejected, read_input, decode_json, encoded,
                         digest, private_root_fd, child_name, open_child, write_file,
                         read_directory, report_error)
from scheduler_source_evidence import read_verified_source_export, assess_scheduler_state


def main():
    parser = SafeArgumentParser(description=__doc__)
    for name in ('export', 'snapshot', 'private-root', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    rfd = ofd = None
    try:
        originals, evidence = read_verified_source_export(args.export)
        raw = read_input(args.snapshot, '.json')
        proof_raw = read_input(Path(args.snapshot).parent / 'manifest.json', '.json')
        proof = decode_json(proof_raw)
        if (not isinstance(proof, dict) or proof.get('kind') != 'private_extracted_workflow_analysis_v2'
                or proof.get('files_sha256', {}).get('current-snapshot.original.private.json') != digest(raw)
                or proof.get('state_modified') is not False):
            raise Rejected('PRIVATE_SNAPSHOT_PROOF_MISMATCH')
        records = decode_json(raw)
        if not isinstance(records, list) or any(not isinstance(record, dict) or not isinstance(record.get('id'), str) for record in records):
            raise Rejected('EXPECTED_WORKFLOW_SNAPSHOT_ARRAY')
        assessment = [{'source_index': i, 'workflow_id': record['id'],
                       'state': assess_scheduler_state(record, evidence)}
                      for i, record in enumerate(records, 1)]
        files = dict(originals)
        files.update({
            'SHA256SUMS': ''.join(f'{checksum}  {name}\n' for name, checksum in evidence['export_manifest'].items()).encode(),
            'EXPORTED': b'STATIC_SOURCE_EXPORTED: verified private copy, no execution.\n',
            'snapshot.original.private.json': raw, 'snapshot-proof.private.json': proof_raw,
            'source-evidence.private.json': encoded(evidence),
            'state-assessment.private.json': encoded(assessment),
        })
        files['manifest.json'] = encoded({'kind': 'native_scheduler_state_review_v1',
            'files_sha256': {name: digest(value) for name, value in files.items()},
            'state_modified': False, 'source_promotion_approved': False,
            'conversion_approved': False, 'workflow_execution_performed': False,
            'historical_runtime_compatibility_established': False})
        files['REVIEW_ONLY'] = b'Private native-state assessment only; no reset, import or conversion approval.\n'
        root, rfd = private_root_fd(args.private_root)
        name = child_name(root, args.output)
        ofd = open_child(rfd, name, create=True)
        for filename, content in files.items():
            write_file(ofd, filename, content)
        if read_directory(ofd, set(files)) != files:
            raise Rejected('PRIVATE_REVIEW_COPY_MISMATCH')
        _, copied_evidence = read_verified_source_export(root / name)
        if copied_evidence != evidence:
            raise Rejected('SOURCE_PROVENANCE_MISMATCH')
        b = sum(item['classification'] == 'B' for entry in assessment for item in entry['state'])
        c = sum(item['classification'] == 'C' for entry in assessment for item in entry['state'])
        print(f'Private source review validated: native class-B fields={b}; unknown class-C fields={c}.')
        print('Original state unchanged; no import, reset, conversion or historical-runtime approval.')
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, RecursionError) as error:
        report_error(error)
        return 1
    finally:
        for fd in (ofd, rfd):
            if fd is not None:
                os.close(fd)
    return 0


if __name__ == '__main__':
    sys.exit(main())
