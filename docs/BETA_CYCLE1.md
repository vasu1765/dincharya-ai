# Integrated personal beta implementation cycle 1

Development base `6b486f65c0b91683633402d263a776e862a809aa`. Gate 1 is blocked.

## Implemented and exercised

Python 3.12.14 executed all 11 original pin and preflight tests. The source verifier matched all 16 reviewed blobs and the inert-plan CLI passed. The combined suite now executes 16 tests with zero skips. Compilation passed. No manifest bytes changed.

- `python3 -m dincharya.beta_preview` accepts a recorded Telegram private message on stdin for synthetic owner 101. It uses the shared parser, preserves explicit offsets and emits a proposal. Tests cover once, daily, weekly and yearly, Hindi/Hinglish/English, identity rejection and withholding lunar recurrence. This simulator has no callback, write or send path.
- `python3 -m dincharya.beta_storage PLAN` renders only the storage profile after a digest has been supplied. The checked-in plan correctly refuses rendering pending image review. A synthetic digest is used only in unit tests. The profile specifies private PG storage, socket-only access, no pulls or automatic restart, and a PG17 health test. No services have been started. Bootstrap is a privileged initialization role and must never become an application login. Before any startup, independently verify the absence of the project volume, review the official image digest and use a new external bootstrap secret.
- `python3 -m dincharya.beta_observer ALIAS REV --samples N` samples a separately managed, pinned SSH forced status command. Only run with synthetic inputs until the monitor host and target are approved. Missing relay evidence, wrong target/revision and quarantine are visible. Output includes simulated owner alert transitions. Its available state describes the relay response only. Worker freshness, backlog age, host fencing and real alert delivery still need independent verification.
- `python3 -m dincharya.beta_archive DIRECTORY CERTIFICATE PEM_SHA256` seals stdin locally. A disposable test verifies certificate pin rejection, encrypted round trip, ciphertext identity and failed authentication after tampering. The caller must establish successful dump completion before invoking the sealer. Transfer, scheduling and PG restore have separate gates. Never pipe unverified decrypted output into a live database.

## Artifact decision and operations

Use the exact review IDs in beta-source-pins.json and the artifact table in M2B_SOURCE_ADOPTION.md. Keep 0015 (blob dd4d76d4855f08c79c224128979d44efb57ee100) synthetic-only. The accepted connection factory explicitly checks dincharya_app_test. A personal connection cannot be made by switching an environment variable. Owner decision needed: identify and authorize the exact schema-only artifact and checksum for fresh personal-beta use, or commission a separately reviewed repository-owned personal schema. No private manifest or existing database is needed for this decision. Require new beta-specific migration and role review, including paired receipts and no direct worker DML. Existing migration history stays intact.

Before attended operation, integrate the owner-only gateway, signed dispatcher, scheduler and singleton worker with that schema; enforce the civil-only policy on persisted approval and projection paths, review every image and dependency pin, and test conflict, status, pause/resume/cancel, read-only guarded historical answers and paired receipt/quarantine using the actual new runtime. The storage profile cannot run the application today. Stage 1/2 and PR #17 retain their original scopes.

On uncertainty, stop the affected worker and poller, preserve records and inspect receipt evidence. A second host requires explicit fencing of the first and fresh owner review of restored pending actions. Independent off-device transfer, restore and external failure notification remain outstanding for unattended operation.

## One Acer Codex task

Fetch the draft PR head into a fresh detached worktree and verify its SHA against GitHub. With the accepted offline gateway/astronomy Python environment, run the following from its root. Stop on failure or skipped required tests. Record revision, counts and exit codes in the PR. These checks use no Docker, private configuration or Telegram connection. Native beta database integration requires the personal schema and reviewed images first.

```bash
set -eu
python -B -m unittest discover -s tests -p 'test_recurring.py' -v
python -B -m unittest discover -s tests -p 'test_historical_panchang.py' -v
python -B -m unittest discover -s tests -p 'test_beta*.py' -v
python -B scripts/check-beta-source-pins.py
python -B -m dincharya.beta_preflight docs/beta-runtime-plan.json
```
