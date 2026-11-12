#!/usr/bin/env python3
"""Validate explicit private candidates and provenance; never promotes to Git."""
import sys
from source_sync import SafeArgumentParser, report_error, validate_bundle


def main():
    parser = SafeArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--private-metadata', required=True)
    parser.add_argument('--private-root', required=True)
    args = parser.parse_args()
    try:
        validate_bundle(args.bundle, args.private_metadata, args.private_root)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, RecursionError) as error:
        report_error(error)
        return 1
    print('Private candidate structure/integrity passed. No Git, import, SQL execution, or recovery approval.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
