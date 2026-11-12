# Administrator-only selective archive extraction

The planner performs no Docker actions. It reads only explicit TOC/archive/checksum
inputs and writes a new private plan outside Git. If sandbox file permissions
prevent reading an artifact, run it in the normal Ubuntu terminal. Do not weaken
private file permissions to work around sandbox mapping.

Replace paths below. Create an owned mode-700 root; output must not exist:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/plan-version-extraction.py plan \
  --toc /private/phase2b/n8n-toc.txt \
  --archive /private/baseline/n8n.dump \
  --checksum-manifest /private/baseline/SHA256SUMS \
  --private-root /private/new-owned-mode700-root \
  --output /private/new-owned-mode700-root/authorized-tables \
  --client-image postgres:17
```

The planner streams the archive checksum against its exact manifest entry and
rejects symlink/nonregular inputs. It selects exactly public TABLE and TABLE DATA
entries for workflow_history, workflow_published_version, workflow_publish_history.
It rejects missing/duplicate IDs, other schemas, malformed selection and unsafe
mount path delimiters. The numeric IDs/table names are safe to review; owner
columns and full TOC remain in private files. No unapproved table is selected.

Review the six-entry output and generated extract-authorized.sh, then run it from
the normal terminal (never from the Codex sandbox):

```bash
bash /private/new-owned-mode700-root/authorized-tables/extract-authorized.sh
```

The generated exact command pins the existing local postgres:17 image by immutable
ID; --pull=never prevents downloads. It verifies pg_restore 17.11 in a temporary
container. Containers have --network=none, read-only root filesystem, no capabilities,
no-new-privileges, and the administrator's UID/GID. Only the archive and selected
TOC are mounted read-only; no live data volumes or environment credentials are used.
The entrypoint is pg_restore, never PostgreSQL's server initialization script.

Before extraction it rechecks the archive checksum, obtains a fresh --list from
the same archive and compares the six exact selected lines with the plan. The
extraction uses --use-list=/input/authorized.list --file=-, --exit-on-error,
--no-owner, --no-privileges, --no-comments, --no-security-labels. There is no
--dbname, --create, --clean or SQL execution. No dependency table is added.
After extraction it rechecks the archive and exclusively finalizes the SQL file.
Successful completion yields authorized-tables.sql, SHA256SUMS and EXTRACTED.

All outputs/logs are mode 600 under the new mode-700 plan directory. Errors remain
private; the terminal prints fixed status text. Noclobber/exclusive creation makes
rerunning into an existing plan fail rather than overwrite. Failed output is not
valid without EXTRACTED. Do not execute/import the SQL or print it in chat.
No deletion of source/backups occurs; only the newly created SQL partial name is
removed after an exclusive hard-link finalization preserves its complete data.

Planner and shell syntax/selection are covered by synthetic tests. The end-to-end
test puts a fake docker executable first in a sanitized PATH; it never accesses
Docker. Real pg_restore filtering has not been executed or integration-tested by
Codex. The administrator run is the next action, not evidence of a restore/import.

For scheduler investigation, provide approved offline Schedule Trigger source
and directly imported helper implementations from the verified n8n 2.47.3 image,
plus package/image provenance. Do not provide credentials, mounts or environment
values. Do not assume local version attestation proves the backup's historical
runtime or the published workflow's content. State stays unchanged/class C until
implementation evidence supports a classification and treatment is approved.
