#!/usr/bin/env python3
"""Private static inspection of an authorized workflow snapshot. Never executes JS."""
import os
import sys
from pathlib import Path
from source_sync import (SafeArgumentParser, Rejected, read_input, digest, private_root_fd,
                         open_child, child_name, write_file, read_directory,
                         validate_workflow_snapshot, report_error)
from workflow_security import security_payload, validate_security_files


def main():
    parser = SafeArgumentParser(description=__doc__)
    for argument in ('snapshot', 'prior-review', 'prior-root', 'private-root', 'output'):
        parser.add_argument('--' + argument, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    root_fd = output_fd = None
    try:
        # Only explicitly authorized prior artifacts are read; no database lookup.
        prior = validate_workflow_snapshot(args.prior_review, args.prior_root)
        raw = read_input(args.snapshot, '.json')
        if (prior['source_path'] != str(Path(args.snapshot).absolute())
                or prior['files_sha256']['workflow-input.private.json'] != digest(raw)):
            raise Rejected('PRIOR_VERIFIED_INPUT_MISMATCH')
        files, report = security_payload(raw)
        root, root_fd = private_root_fd(args.private_root)
        output_fd = open_child(root_fd, child_name(root, args.output), create=True)
        for name, content in files.items():
            write_file(output_fd, name, content)
        stored = read_directory(output_fd, set(files))
        validate_security_files(stored)
        print('Private static review validated: workflows=' + str(report['workflow_count'])
              + ', Code nodes=' + str(report['code_node_count']) + '.')
        print('No execution, state transformation, source promotion or conversion approval.')
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, RecursionError) as error:
        report_error(error)
        return 1
    finally:
        for fd in (output_fd, root_fd):
            if fd is not None:
                os.close(fd)
    return 0


if __name__ == '__main__':
    sys.exit(main())
