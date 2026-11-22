# Combined Stage 1 WSL integration

The targeted confirmation recheck passed at its previously recorded revision. Preserve its result and both earlier stopped projects. This fresh run uses the existing first-confirmation verifier as the entry gate for a timed civil appointment journey.

| Behavior | Required independent observation | Latest result |
|---|---|---|
| Timed delivery | Two distinct accepted recorder attempts pair with the two PostgreSQL message IDs, owner chat and correct due minutes. The second occurs after service recovery. | **PASS** — two paired recorder/SQL receipts, second after outage recovery. |
| Silent appointment | An owner-approved silent event passes its due time with zero slots, legacy rows or recorder attempts for it. | **PASS** — due time passed with zero silent slots or attempts. |
| Uncertain outcome | One durable recorder attempt, one uncertain SQL slot without receipt, no replay after restart and subsequent worker ticks. | **PASS** — one uncertain attempt, no receipt or replay after restart/ticks. |
| Worker exclusion | A second real worker exits with the dedicated lock-busy code while the original continues processing. | **PASS** — competing worker exit 75; original worker continued. |
| Restart and persistence | Gateway, application and worker stop, the final reminder becomes due during the outage, then recovery retains history, catches up once and rejects a stale button. | **PASS** — durable histories retained, catch-up once, stale button rejected. |
| Health and backup/restore | Signed health reflects the quarantine and detects outage. A quiesced local CMS-encrypted dump restores to a fresh networkless PG17 instance. Migration checksums and six table histories match. | **PASS** — outage/quarantine health; local encrypted restore and six history matches. |

The recorder commits title, synthetic receipt sequence and real UTC clock in the same SQLite transaction as its attempt. The independent database checks use the actual civil due time, attempt status, receipt pair, approved control and audit counts. An invented lost response returns no receipt to the application. The overdue delivery has a three-minute upper bound in this test. Operational delivery settings are unchanged.

**Work results:** 11 focused staging tests passed, including three new checks covering durable recorder evidence, rejection of incorrect recipient/receipt/time and rejection of silent or duplicate attempts. Bash syntax, Python compilation and explicit safe-source checks passed. Work has no Docker engine for the native acceptance. A local restore pass would cover this synthetic dump only. Off-host backup custody and physical laptop readiness remain separate gates.

## One instruction for WSL Codex

Use a clean checkout at the full reviewed revision supplied with this task. Reuse the accepted WSL Python and public DE440s path from the successful PR #15 recheck. Set REV independently to the supplied commit. From the repository root run once:

```bash
REV="$REV" PY="$PY" KERNEL="$KERNEL" bash staging/laptop/run_complete.sh
```

The script checks the accepted daemon and image, obtains the PostgreSQL and n8n image IDs by read-only container metadata, and builds only a networkless staging-service overlay. It refuses an existing complete project. Its only application project is dincharya-stage1-complete. Preserve original and recheck containers, volumes and state. The restore helper removes only its own transient networkless verification container. The final trap stops the five new services and compares inventories for both earlier projects.

Wait through the real due minutes and the controlled service outage. Capture PASS lines, sanitized counters, journey/stop exit codes and inventory comparison. A first failure ends the run. Preserve the stopped project for investigation; do not replay decisions, delete volumes or proceed to Windows or Telegram acceptance. Record full runtime success only after both exit codes are zero and the script itself exits zero.

## Verified WSL run — 19 November 2026

**PASS — all six checks. Journey exit 0; stop exit 0; script exit 0.**
The approved command executed **once** at clean revision
`da6d08e2b583266af7615f9a5b86de9f6bd66131` on
`development/stage1-confirmation-recheck`. The existing verified Python runtime
and public DE440s were recovered from prior acceptance evidence, then dependency
versions and kernel bytes checked. The accepted daemon and local image were
reused. Only the reviewed staging module was overlaid, with no build network or
dependency retrieval. No application source or accepted migration was changed.

### Sanitized results

- First silent confirmation and its duplicate: one matching approved reply,
  zero fallback replies, no keyboard, committed-control match true. The first
  gate independently observed one event/control/audit and zero slots/deliveries.
- Final persisted schedules/controls/audits: **4 / 4 / 4**. Notification slots:
  **3**; legacy delivery rows: **0**. The stale preview did not add a schedule.
- Durable simulated transport attempts: **3**: **2 accepted, paired receipts**
  and **1 uncertain, unreceipted attempt**. Silent attempts: **0**. No extra
  attempt or uncertain replay after recovery and subsequent worker ticks.
- Civil due times and recorder UTC timestamps matched the slots. Both accepted
  receipts matched the owner and recorder identities internally; identifiers and
  payloads were not published. Recovery delivery remained within the existing
  test's three-minute bound; no system-clock change.
- Second real worker was excluded with dedicated **exit 75**, while the original
  continued. Gateway/app/worker were stopped for the controlled outage; signed
  health detected it. Recovery retained accepted and uncertain recorder history,
  caught up the final reminder once and rejected the pre-restart review ticket.
- Recovery health: relay ready; due **0**, sending **0**, dead **0**, uncertain **1**.
- Quiesced synthetic PostgreSQL dump, temporary synthetic RSA certificate and
  CMS encryption/decryption succeeded. A new networkless PostgreSQL restore
  matched migration checksums and all **six** tracked table histories. Restored
  totals: slots **3**, sent **2**, uncertain **1**. Its transient container was
  removed. This is local synthetic restore evidence, not off-host custody or
  operational role-rebind acceptance.

### Stop and preservation

The exit trap stopped all five complete-project services and verified both
prior-project inventories. A separate read-only final inspection additionally
verified the exact prior container states, all unrelated running/container and
volume inventories, and the absence of any unexpected remaining helper/resource.
Each complete-project container exited **0**. Its four named volumes and stopped
containers remain preserved; there were no mounts into either earlier project.
Original Stage 1 and targeted recheck state/volumes were not replayed or modified.

No mismatch occurred. The original Stage 1 failure remains historical evidence;
this fresh success does not reproduce or explain it. No already accepted suite
was repeated; only the new combined integration command and prerequisite/static
checks ran. No real Telegram, private baseline, Windows power change, reboot,
startup registration, permanent deployment, source promotion or merge occurred.
Stage 2 physical and off-host acceptance remains separately authorized work.

Only this report and HANDOFF changed after the runtime finished. Explicit
safe-source and diff checks passed on those documentation changes. Git metadata
is read-only; exact documentation commit commands are in HANDOFF.
