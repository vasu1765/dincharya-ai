# One attended Windows/WSL laptop acceptance task

Stage 1 passed all six integration checks. Stage 2 uses the same locally verified images, relay, approvals and slot worker. No image build or dependency retrieval is needed. The fixed new project is `dincharya-stage2-physical`. Its controller creates fresh synthetic data and a persistent phase journal. The driver never initiates a Windows reboot, edits a power plan, registers a task or contacts Telegram. Manual recovery after interactive login is the acceptance target.

## Before arming the timed fixtures

Use the full reviewed PR revision on all devices. Reserve about 65 minutes on AC with the owner present. Agree on one reboot window around minute 32 and the backup destination before starting the clock. The recovery machine must have a verified local PG17 image, its own approved Docker daemon, the recipient's test private key, Python 3.11+, OpenSSL and a clean checkout. A network filesystem on another physical device must support hard links. Keep its exact mount source, directory, RSA public-certificate DER digest and recovery host identity in the private execution scope.

1. **Windows, read only.** Run `& .\staging\laptop\host.ps1 -Mode Power` in PowerShell. Verify the effective **AC** lid action is Do nothing, AC idle standby and hibernation timeouts are zero, and critical-battery/thermal protections remain enabled. Note active scheme and original AC values. Do not proceed on conflicting OEM or managed policy, blocked vents, battery operation or an unverified setting. Any changes and later restoration of specific values need owner approval. The previous [power runbook](LAPTOP_STAGING.md) lists the AC-only commands.
2. **WSL setup.** Set `REV` independently to the reviewed head, `PY` to the previously accepted Python interpreter and `KERNEL` to the verified public DE440s path. Use the pinned laptop daemon with its three preserved, stopped Stage 1 projects. Run from the repository root. Use this same environment and helper after login:

```bash
export REV PY KERNEL PYTHONDONTWRITEBYTECODE=1
physical() { "$PY" -B staging/laptop/physical.py "$@"; }
physical prepare
physical status
```

3. **Independent observer.** Use a second powered device with a synchronized clock and an existing owner-approved, host-key-pinned SSH alias restricted to returning only `physical status` from the approved checkout. No remote start command or Docker socket. Status checks AC and signed application health. If this endpoint is unavailable, pause before arming. Creating an SSH service or granting new access requires separate approval. On the independent device run the following in an attended terminal. Use a fresh local output file, keep the observer running through reboot, and verify several ready samples with the correct revision before proceeding.

```bash
set -o noclobber
python3 -B staging/laptop/observer.py "$APPROVED_ALIAS" --stage2-revision "$REV" --samples 240 >stage2-observer.jsonl
```

## Timed physical sequence

Run each command exactly once at its checkpoint. Keep Windows locked while the lid is closed. The owner records actual close/open times independently, allows at least 30 complete minutes physically closed, and watches for AC loss, overheating or an unexpected monitor alert. Opening early invalidates the interval. Do not retry an approval or adjust the clock.

| Checkpoint | Operator action and required evidence |
|---|---|
| Arm and close | In WSL run `physical arm` followed immediately by `physical closed`. Lock Windows and close the lid. Six synthetic civil events have distinct minutes relative to the arm minute: silent +3, reminders +5 and +20, outage +35, recovered +45, uncertain +47. Save that timetable. |
| Open | After 30 full minutes physically closed, reopen and run `physical open`. It checks elapsed time, AC, unchanged Windows boot time and System sleep events. The external log must show continuous ready samples. |
| Interrupt | With the specific reboot approval in hand, run `physical interrupt` around +31/+32. It verifies two paired receipts and stops only Stage 2. The independent observer should signal outage after two misses. Close other personal work and have the owner perform the approved normal Windows reboot. |
| Recover | Remain at the Windows login screen through the +35 due minute. Log in, start the accepted Docker Desktop engine manually if required, reopen WSL, restore the shell variables/helper above and run `physical recover` promptly. The driver checks Windows boot time changed and starts the same Stage 2 stack. The overdue reminder must be recorded within three minutes of its due time. If that window is missed, inspect and mark the recovery check incomplete. |
| Verify | After +48, stop the observer and provide its sanitized JSONL as `OBSERVER_LOG` in WSL. Export that variable and run `physical verify`. Require four paired PostgreSQL/recorder receipts, zero silent attempts, exactly one uncertain attempt and a single worker holding the database lock. The driver checks stable observer cadence, a closed-lid window, outage and subsequent recovery. It quiesces writers and saves six table hashes. |
| Export | **Only after explicit transfer approval** set and export `OFFHOST`, `APPROVED_MOUNT_SOURCE`, `CERT`, `CERT_SHA256` and `APPROVED_STAGE2_EXPORT="$REV"` to the approved values. The environment flag records the operator's approval check; it cannot grant authority. Run `physical export`. This validates the mount source and certificate pin, exports only the encrypted synthetic PostgreSQL archive, stops the database and compares all three prior project inventories. |
| Independent restore | The local manifest is `$HOME/.local/state/dincharya-stage2-physical/physical/restore-manifest`. Include this small hash manifest in the approved transfer; communicate its SHA-256 over an independent trusted channel. On the approved recovery host set and export `REV MANIFEST MANIFEST_SHA256 OFFHOST TEST_KEY PG RECOVERY_DAEMON`. Here PG is the full reviewed local PG17 image ID and OFFHOST is the receiver's archive directory. Run `python3 -B staging/laptop/physical_restore.py`. Only the transient networkless verification container is removed. Migration checksums, six table histories, four sent slots and one uncertain slot must match. |

## Interruptions, rollback and reporting

At any unexpected send, safety concern, AC loss, early lid opening, changed inventory or checkpoint failure, open the lid and stop advancing. Run `physical inspect` to list durable phase reservations and completions. A started phase without a completion marker is uncertain. Never remove a reservation, rerun the phase, reset a slot or resume a partial approval. After preparation, `physical stop` aborts the session and gracefully stops only the new project, retaining its state and volumes. If preparation failed before journal creation, inspect the new project's resources by exact project label and authorize scoped recovery before mutation. Preserve any incomplete archive and its receipt history. Do not use a global Docker cleanup.

Restore only host settings explicitly changed under a separate approved plan, using the recorded scheme and AC values; re-query the effective settings. Stop the attended observer. Record local UTC times, observed login method, readiness gaps, counts, exit results and archive/restore integrity outcomes. Keep keys, endpoint identifiers, personal data and raw database artifacts private. A missing independent log, unapproved transfer, or incomplete restore leaves the corresponding gate pending. Stage 1 evidence stands independently. Neither a physical pass nor this runbook enables unattended or live operation.
