#!/usr/bin/env python3
"""Prepare/validate private raw-snapshot candidates. Never evaluates workflow code."""
import os
import sys
from source_sync import (SafeArgumentParser, prepare_workflow_snapshot,
                         validate_workflow_snapshot, report_error)


def main():
    parser = SafeArgumentParser(description=__doc__)
    parser.add_argument('--snapshot')
    parser.add_argument('--integrity-report')
    parser.add_argument('--output', required=True)
    parser.add_argument('--private-root', required=True)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    if not args.validate_only and (not args.snapshot or not args.integrity_report):
        parser.error('Missing explicit inputs')
    os.umask(0o077)
    try:
        if args.validate_only:
            result = validate_workflow_snapshot(args.output, args.private_root)
        else:
            result = prepare_workflow_snapshot(args.snapshot, args.integrity_report,
                                               args.output, args.private_root)
            validate_workflow_snapshot(args.output, args.private_root)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError) as error:
        report_error(error)
        return 1
    print(f'Private workflow checks passed: converted={result["converted_count"]}, rejected={result["rejected_count"]}.')
    print('Import compatibility, publication state and Git promotion are NOT approved.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
