#!/usr/bin/env python3
"""Plan exact offline extraction for an administrator. Planning never calls Docker."""
import hashlib
import os
from pathlib import Path
import re
import shlex
import sys
from source_sync import (SafeArgumentParser, Rejected, read_input, private_root_fd,
                         child_name, open_child, write_file, encoded, digest, report_error)
from version_evidence import plan_authorized_toc


def selected_list(toc):
    entries = plan_authorized_toc(toc)
    ids = {entry['entry_id'] for entry in entries}
    selected = []
    all_ids = set()
    for line in toc.splitlines():
        match = re.match(r'^(\d+);', line)
        if not match:
            continue
        identity = int(match.group(1))
        if identity in all_ids:
            raise Rejected('DUPLICATE_TOC_IDENTIFIER')
        all_ids.add(identity)
        if identity in ids:
            selected.append(line)
    if len(selected) != 6:
        raise Rejected('AMBIGUOUS_SELECTION')
    return ('\n'.join(selected) + '\n').encode(), entries


def verify_archive(archive, manifest):
    archive, manifest = Path(archive).absolute(), Path(manifest).absolute()
    if archive.name != 'n8n.dump' or manifest != archive.parent / 'SHA256SUMS':
        raise Rejected('UNEXPECTED_ARCHIVE_OR_MANIFEST')
    lines = read_input(manifest, '').decode().splitlines()
    entries = []
    for line in lines:
        match = re.fullmatch(r'([0-9a-fA-F]{64}) ([ *])(.+)', line)
        if match and match.group(3) in {'n8n.dump', './n8n.dump'}:
            entries.append(match.group(1).lower())
    if len(entries) != 1:
        raise Rejected('EXACT_CHECKSUM_ENTRY_REQUIRED')
    # Streaming hash only; no archive parser or extraction is invoked here.
    import stat
    fd = os.open(archive, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise Rejected('ARCHIVE_NOT_REGULAR')
        hasher = hashlib.sha256()
        with os.fdopen(os.dup(fd), 'rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                hasher.update(chunk)
        after = os.fstat(fd)
        if ((before.st_size, before.st_mtime_ns, before.st_ctime_ns) !=
                (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                or hasher.hexdigest() != entries[0]):
            raise Rejected('ARCHIVE_INTEGRITY_FAILED')
    finally:
        os.close(fd)
    return entries[0]


def administrator_script(archive, output, planner, image):
    paths = [str(Path(value).absolute()) for value in (archive, output, planner)]
    if any(any(char in path for char in '\n\r,') for path in paths):
        raise Rejected('UNSUPPORTED_MOUNT_PATH')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_./:@-]*', image):
        raise Rejected('INVALID_CLIENT_IMAGE_REFERENCE')
    archive, output, planner = map(shlex.quote, paths)
    image = shlex.quote(image)
    return f'''#!/usr/bin/env bash
+# Administrator execution only; planner itself never invokes Docker.
+set +x
+set -Eeuo pipefail
+umask 077
+exec 4>&2
+cd -- {output}
+set -C
+exec 2>extraction.private.log
+trap 'printf "Offline extraction failed; inspect private logs. No database restore was requested.\\n" >&4' ERR
+for tool in docker python3 sha256sum id; do command -v "$tool" >/dev/null; done
+image_id="$(docker image inspect --format '{{{{.Id}}}}' {image})"
+[[ "$image_id" =~ ^sha256:[0-9a-f]{{64}}$ ]]
+printf '%s\\n' "$image_id" > client-image.private.txt
+docker_args=(run --rm --pull=never --network=none --read-only --cap-drop=ALL
+  --security-opt=no-new-privileges --user "$(id -u):$(id -g)" --entrypoint pg_restore)
+docker "${{docker_args[@]}}" "$image_id" --version > client-version.private.txt
+python3 -B -c 'from pathlib import Path; import re; assert re.fullmatch(r"pg_restore \\(PostgreSQL\\) 17\\.11(?:[^\\n]*)\\n?",Path("client-version.private.txt").read_text())'
+# Recheck the source hash before any archive listing or extraction.
+python3 -B {planner} verify-archive --archive {archive} --expected-list authorized.list --expected-hash-file archive-sha256.private.txt
+mounts=(--mount "type=bind,src="{archive}",dst=/input/n8n.dump,readonly")
+docker "${{docker_args[@]}}" "${{mounts[@]}}" "$image_id" --list /input/n8n.dump > fresh-toc.private.txt
+python3 -B {planner} verify-toc --toc fresh-toc.private.txt --selected-list authorized.list
+# Exact TOC IDs only. No --dbname/--create/--clean and no connection options.
+docker "${{docker_args[@]}}" "${{mounts[@]}}" \\
+  --mount "type=bind,src=$(pwd -P)/authorized.list,dst=/input/authorized.list,readonly" \\
+  "$image_id" --exit-on-error --no-owner --no-privileges --no-comments --no-security-labels \\
+  --use-list=/input/authorized.list --file=- /input/n8n.dump > authorized-tables.sql.partial
+test -s authorized-tables.sql.partial
+python3 -B {planner} verify-archive --archive {archive} --expected-list authorized.list --expected-hash-file archive-sha256.private.txt
+python3 -B -c 'import os; os.link("authorized-tables.sql.partial", "authorized-tables.sql"); os.unlink("authorized-tables.sql.partial")'
+sha256sum authorized.list fresh-toc.private.txt client-image.private.txt client-version.private.txt authorized-tables.sql > SHA256SUMS
+printf '%s\\n' 'EXTRACTION_COMPLETED: selected SQL only; never executed or restored. Review privately before parsing.' > EXTRACTED
+printf 'Offline selected-table extraction completed. All content remains private.\\n'
+'''.replace('\n+', '\n').encode()


def main():
    parser = SafeArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    plan = sub.add_parser('plan')
    for name in ('toc', 'archive', 'checksum-manifest', 'private-root', 'output'):
        plan.add_argument('--' + name, required=True)
    plan.add_argument('--client-image', default='postgres:17')
    check = sub.add_parser('verify-toc')
    check.add_argument('--toc', required=True)
    check.add_argument('--selected-list', required=True)
    check_archive = sub.add_parser('verify-archive')
    check_archive.add_argument('--archive', required=True)
    check_archive.add_argument('--expected-hash-file', required=True)
    check_archive.add_argument('--expected-list', required=True)
    args = parser.parse_args()
    root_fd = output_fd = None
    try:
        if args.action == 'verify-toc':
            selected, _ = selected_list(read_input(args.toc, '.txt').decode())
            if selected != read_input(args.selected_list, '.list'):
                raise Rejected('FRESH_TOC_SELECTION_MISMATCH')
        elif args.action == 'verify-archive':
            # Marker must itself still describe exactly the three authorized tables.
            selected_list(read_input(args.expected_list, '.list').decode())
            expected = read_input(args.expected_hash_file, '.txt').decode().strip()
            actual = verify_archive(args.archive, Path(args.archive).parent / 'SHA256SUMS')
            if actual != expected:
                raise Rejected('PLANNED_ARCHIVE_CHANGED')
        else:
            toc_bytes = read_input(args.toc, '.txt')
            selected, entries = selected_list(toc_bytes.decode())
            expected = verify_archive(args.archive, args.checksum_manifest)
            root, root_fd = private_root_fd(args.private_root)
            name = child_name(root, args.output)
            script = administrator_script(args.archive, args.output, __file__, args.client_image)
            output_fd = open_child(root_fd, name, create=True)
            write_file(output_fd, 'authorized.list', selected)
            write_file(output_fd, 'archive-sha256.private.txt', (expected + '\n').encode())
            write_file(output_fd, 'plan.private.json', encoded({'entries': entries, 'toc_sha256': digest(toc_bytes),
                        'docker_executed': False, 'extraction_performed': False}))
            write_file(output_fd, 'extract-authorized.sh', script)
            for entry in entries:
                print(entry['entry_id'], entry['kind'], entry['schema'] + '.' + entry['table'])
            print('Private plan prepared. Administrator must review and run extract-authorized.sh outside the sandbox.')
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
