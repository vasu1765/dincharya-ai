#!/usr/bin/env python3
"""Scan only explicitly named non-secret source paths; never traverses backups."""
from pathlib import Path
import sys
from source_sync import PROJECT, Rejected, SafeArgumentParser, read_input, scan_text


def check_path(value):
    path = Path(value)
    resolved = path.resolve()
    if PROJECT not in resolved.parents or path.is_symlink():
        raise Rejected('SCAN_PATH_OUTSIDE_PROJECT')
    relative = resolved.relative_to(PROJECT)
    if (any(part in {'.git', '.venv', 'venv', 'backups', 'captures', 'private',
                     'secrets', 'credentials', 'node_modules'} or part.startswith('baseline-')
            for part in relative.parts[:-1])
            or relative.name.startswith('.env')
            or relative.name in {'PREPARED', 'workflows.candidate.json', 'manifest.json'}
            or any(part in relative.name.lower() for part in ('workflow-input', 'workflow-provenance', 'encryption-key'))
            or relative.suffix not in {'.py', '.md', '.yaml', '.yml', '.json', '.sql', '.txt'}):
        # .gitignore is the sole extensionless source exception.
        if relative != Path('.gitignore'):
            raise Rejected('FORBIDDEN_SCAN_PATH')
    # Inspect only explicit text source; never open a rejected path.
    content = read_input(resolved, resolved.suffix)
    scan_text(content.decode('utf-8'))


def main():
    parser = SafeArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+')
    args = parser.parse_args()
    failed = False
    for index, value in enumerate(args.files, 1):
        try:
            check_path(value)
        except (OSError, ValueError, UnicodeError, RecursionError):
            # Index only: no secret-bearing paths, values, or exceptions are echoed.
            print(f'Source check rejected input #{index}; review locally.', file=sys.stderr)
            failed = True
    if failed:
        return 1
    print('Explicit source checks passed. Human diff/privacy review is still required.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
