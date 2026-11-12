# Baseline capture

Run `scripts/capture-baseline.sh` manually from an authorized Ubuntu WSL2 terminal.
The script is not run automatically. It does not initialize Git, install tools,
restart containers, run migrations, execute application functions, or import or
publish workflows. Existing Python, SQL, and Compose configuration is unchanged.

## Run

Choose an existing local storage location outside this project and any Git
repository. Local unencrypted backups are supported. Create a private destination
and run (replace the example path):

```bash
mkdir -m 700 -- /absolute/path/to/private-baselines
BASELINE_BACKUP_ROOT=/absolute/path/to/private-baselines \
  bash scripts/capture-baseline.sh
```

The destination must be absolute, writable, owned by your user, and inaccessible
to group/other users. The script resolves symlinks and rejects destinations inside
the project. It creates a unique `baseline-UTC_TIMESTAMP-RANDOM` directory, mode
700, with backup files created as mode 600 under umask 077. It never changes destination permissions.
The destination must have permissions exactly 700; other modes are rejected.
Before sealing, the script validates ownership and modes of captured payloads
(files 600, directories 700). Checksum and completion files are also created with
mode 600 under the same umask.

These backups are **unencrypted** unless the destination independently provides
storage encryption. No encryption attestation variable is required. The script
neither encrypts files nor verifies storage encryption. Unix permissions do not
protect against Windows administrators or physical disk access. The script does
not install encryption tools or print or export encryption keys.

## Disk-space preflight

Before creating a capture directory, log, or backup file, the script uses `df`
to check available bytes on the destination filesystem. `BASELINE_MIN_FREE_GB`
defaults to **5 GB**, where 1 GB means 1,000,000,000 bytes. A positive decimal
value is required; zero, negative, empty, and malformed values fail preflight.
For example, require 20 GB:

```bash
BASELINE_BACKUP_ROOT=/absolute/path/to/private-baselines \
BASELINE_MIN_FREE_GB=20 bash scripts/capture-baseline.sh
```

This is a starting-space threshold, not an estimate of database sizes, reserved
space, or a guarantee that the capture will fit. Allow room for both databases,
schema, JSON, diagnostics, and future encrypted copies. Concurrent disk usage,
quotas, or growing data can still exhaust space; failures leave no COMPLETE marker.

Dependencies: Bash, Docker with Compose, Python 3, and standard Ubuntu utilities
(`realpath`, `mktemp`, `sha256sum`, `find`, `sort`, `xargs`, `date`, `mv`, `df`, `dirname`). The running
PostgreSQL container must provide `psql`, `pg_dump`, and `pg_restore`; the n8n
container must provide Node.js. No tools are installed. Docker must work without
sudo. Both services must be running, and PostgreSQL must report healthy.

The application database defaults to `dincharya_app`. An explicitly empty override
is rejected. Both application and n8n database names must match
`[A-Za-z_][A-Za-z0-9_]*`, with at most 63 ASCII characters. Connection strings,
URIs, quoted identifiers, whitespace, and punctuation are rejected. Names are
passed literally; case is not folded. Override only if verified:

```bash
BASELINE_BACKUP_ROOT=/absolute/path/to/private-baselines \
BASELINE_APP_DB=verified_application_database bash scripts/capture-baseline.sh
```

The n8n database name is taken from the running n8n container. PostgreSQL access
uses the existing `POSTGRES_USER` inside the database container and local socket
authentication at `/var/run/postgresql`, port 5432, explicitly excluding inherited
host/port settings. If local authentication disallows this, capture fails; the script
does not weaken authentication or request a password interactively.

## Database identity gate

Before either dump or schema capture, a read-only `pg_catalog` query verifies
`current_database()` and requires exactly one non-system schema containing all
four tables: `schedule_events`, `recurrence_rules`, `schedule_change_requests`,
and `reminder_deliveries`. Ordinary and partitioned tables are accepted.

The same schema must contain these nine functions:

- `generate_event_occurrences`
- `find_schedule_conflicts`
- `find_occurrence_conflicts`
- `find_proposed_recurrence_conflicts`
- `validate_recurrence_rule`
- `validate_schedule_proposal`
- `process_schedule_decision`
- `approve_advanced_schedule_add`
- `dispatch_schedule_decision`

No scheduling functions are called. Missing objects, multiple candidate schemas,
or a failed query stop execution before dumps; private runtime metadata/logs may
already exist. This verifies names and object kinds, not function signatures,
bodies, permissions, data contents, or an independently trusted instance identity.
If the real application intentionally spans schemas, this gate fails closed and
requires a reviewed adjustment rather than silently accepting a partial match.

## Artifacts and validation

- `application.dump` and `n8n.dump`: full custom-format logical database backups,
  retaining ownership/ACL metadata and database creation instructions.
- Corresponding `.contents` files: archive tables of contents.
- `application-schema.sql`: complete application DDL, including functions,
  triggers, types, and indexes, without ownership and grant statements.
- `workflows-current.raw.json`, when supported: a **read-only PostgreSQL snapshot,
  NOT a guaranteed n8n-importable workflow export**.
- `workflow-snapshot-summary.json`, when supported: total workflow count and
  individual presence booleans for `Dincharya - Telegram Chat` and
  `Dincharya - Scheduled Reminders`, without node contents or credentials.
- `workflow-export-status.txt`: whether JSON export was supported.
- `runtime.txt`: container image IDs and mounts, plus PostgreSQL/tool versions.
- `database-identity.txt`: successful pre-dump catalog check.
- `capture-status.txt`: database capture, workflow snapshot, full recovery backup,
  restore-test, and backup-encryption statuses.
- Start/end timestamps, private diagnostics, and `SHA256SUMS`.
- `COMPLETE`: atomically finalized marker beginning with `CAPTURE_COMPLETE`,
  written only after database capture, applicable structural checks, and checksum
  verification succeed. It explicitly states `database_capture=completed`,
  `workflow_snapshot=completed` or `unsupported`, and
  `full_recovery_backup=not_completed`. It is not proof of restore or complete
  disaster recovery. An unsupported workflow snapshot never implies workflow
  snapshot completion.

Every PostgreSQL connection requests read-only transactions. Dumps use a bounded
lock wait. Each archive must be nonempty and readable by `pg_restore --list`.
Schema output must be nonempty. This does not prove every schema object is present:
review expected function signatures and the schema contents before accepting the
baseline; the pre-dump identity gate checks names only. Payload files are finalized and checked for leftover
`.partial` artifacts, and diagnostics are closed before generating SHA256SUMS.
The manifest is itself written through a `.partial` file and then finalized.
**SHA256SUMS excludes itself and the COMPLETE marker**, which is created afterward.
No checksummed artifact is modified after hashing. Late-stage stderr goes to a
private sibling file named `baseline-...finalization-RANDOM.private.log`, outside
the capture directory. This mutable operational log is excluded from SHA256SUMS;
it is not a sealed backup payload. Preserve and protect it with the capture.
Checksums detect accidental
changes, not malicious tampering.

The workflow exporter discovers the standard `workflow_entity` table through
read-only catalogs. It checks an array of workflow objects, required fields,
ID/name types, node objects, and connection mappings. It records the total count
and both expected-name booleans in the summary before failing if an expected name
is missing. The summary contains no workflow contents. Structural validation is
not semantic validation by n8n. Multiple matching tables or invalid JSON stop capture. If no
standard table exists (for example a customized prefix), the export is explicitly
marked unsupported; the full n8n dump is still retained. Do not treat that case as
a completed source baseline until a version-aware workflow export is obtained.

Raw rows are PostgreSQL review snapshots, **not guaranteed n8n-importable files**.
Do not feed them directly to an import command. A version-aware, reviewed export
is still needed for portable source-controlled workflows.
Current drafts can differ from published versions. Published versions and history
remain in the full n8n database dump. The script deliberately avoids the n8n CLI:
its initialization could run migrations or other writes. No credentials export
API or workflow execution API is called.

Errors stop execution. Partial artifacts and diagnostics remain private for
investigation, and COMPLETE is absent. Never use partial dumps as accepted
backups. Raw diagnostics are not printed because errors can include sensitive
details. Safe terminal errors identify the capture stage, exit code, and script
line without printing the failed command or its arguments. Raw tool stderr stays
in `diagnostics.private.log` until sealing. Finalization, checksum generation,
checksum verification, and completion-marker errors then go to the private sibling
finalization log. Its path is reported without exposing its contents. Safe error
messages remain available on terminal stderr. Neither diagnostic log is printed
or copied into terminal stdout.
Preflight errors occur before the private log exists and contain only local
validation diagnostics. Review private files locally without pasting them into
chat or Git. A summary file can remain in a failed capture to explain missing
expected workflows. Its presence alone does not indicate successful capture.

To recheck checksums later, from the capture directory:

```bash
sha256sum --check --status SHA256SUMS
```

## Not yet backed up

- n8n encryption key, `.env` files, Telegram token, and external secrets.
- Cluster-global roles, role passwords, tablespaces, and server configuration.
- n8n volume files, filesystem binary data, and installed community/custom nodes.
- Ollama models/configuration, gateway process supervision, and host setup.
- Docker images themselves and an independent/off-device backup copy.

Keys and environment files require a separately approved encrypted process.
Without the correct n8n encryption key, restored stored credentials cannot be
decrypted. Database ownership/grants may require separately recreated roles.

## Security and recovery limitations

Database dumps can contain personal schedules, execution history, and encrypted
credentials. Workflow nodes, pinned data, function bodies, and error logs may
contain plaintext secrets. Files are private but **not encrypted by this script**.
Local unencrypted capture is permitted. Anyone with sufficient Windows or host
administrator access, or physical disk access, may be able to read these backups.
Mode 700/600 and SHA-256 do not provide encryption. Use an approved encrypted
process for off-device copies when needed.
Encryption keys and `.env` files remain excluded pending the separately approved
encrypted backup process; this capture alone is not a complete recovery set.
Keep the backup destination outside all Git repositories and never stage or
commit backups, diagnostic logs, raw captures, or unreviewed schema/workflow
exports. The project .gitignore excludes private captures, dumps, and logs; do
not bypass it with forced staging. Ignore rules are
only a guardrail; they cannot make secret-containing source safe to stage.

Live dumps take ordinary read locks and consume CPU, disk, and I/O. They do not
write database records, but can temporarily contend with DDL. Each database has
its own consistent snapshot; the pair and workflow JSON are not one coordinated
snapshot. Avoid manual configuration/schema edits during capture. The script
does not suppress normal reminders or application writes.

Before declaring recovery proven, restore into isolated PostgreSQL 17 and a
compatible n8n version with separate volumes and ports. Obtain the effective
encryption key, required roles/extensions, filesystem data, custom nodes, and
configuration through separate approved captures. Record the actual n8n version
and retain the image identified by runtime.txt; this script records image IDs
without starting an n8n process. Keep restored n8n isolated from Telegram and all
external services before starting it: restored workflows may be active. Do not
start a second production-token polling gateway. Verify the expected tables,
function signatures, current/published workflows, credential decryption, and data
integrity in isolation. No restore commands in this process target production.
Archive listing checks inspect metadata rather than reading/restoring every data
block. A full isolated restore is required to establish that data can be read,
roles and dependencies can be resolved, and the application can operate with
the separately preserved keys and configuration. Record the restore date,
versions, checks performed, and any remaining failures before relying on recovery.
