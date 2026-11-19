# Combined Stage 1 WSL integration

The targeted confirmation recheck passed at its previously recorded revision. Preserve its result and both earlier stopped projects. This fresh run uses the existing first-confirmation verifier as the entry gate for a timed civil appointment journey.

| Behavior | Required independent observation | Latest result |
|---|---|---|
| Timed delivery | Two distinct accepted recorder attempts pair with the two PostgreSQL message IDs, owner chat and correct due minutes. The second occurs after service recovery. | WSL pending |
| Silent appointment | An owner-approved silent event passes its due time with zero slots, legacy rows or recorder attempts for it. | Timed observation pending |
| Uncertain outcome | One durable recorder attempt, one uncertain SQL slot without receipt, no replay after restart and subsequent worker ticks. | WSL pending |
| Worker exclusion | A second real worker exits with the dedicated lock-busy code while the original continues processing. | WSL pending |
| Restart and persistence | Gateway, application and worker stop, the final reminder becomes due during the outage, then recovery retains history, catches up once and rejects a stale button. | WSL pending |
| Health and backup/restore | Signed health reflects the quarantine and detects outage. A quiesced local CMS-encrypted dump restores to a fresh networkless PG17 instance. Migration checksums and six table histories match. | WSL pending |

The recorder commits title, synthetic receipt sequence and real UTC clock in the same SQLite transaction as its attempt. The independent database checks use the actual civil due time, attempt status, receipt pair, approved control and audit counts. An invented lost response returns no receipt to the application. The overdue delivery has a three-minute upper bound in this test. Operational delivery settings are unchanged.

**Work results:** 11 focused staging tests passed, including three new checks covering durable recorder evidence, rejection of incorrect recipient/receipt/time and rejection of silent or duplicate attempts. Bash syntax, Python compilation and explicit safe-source checks passed. Work has no Docker engine for the native acceptance. A local restore pass would cover this synthetic dump only. Off-host backup custody and physical laptop readiness remain separate gates.

## One instruction for WSL Codex

Use a clean checkout at the full reviewed revision supplied with this task. Reuse the accepted WSL Python and public DE440s path from the successful PR #15 recheck. Set REV independently to the supplied commit. From the repository root run once:

```bash
REV="$REV" PY="$PY" KERNEL="$KERNEL" bash staging/laptop/run_complete.sh
```

The script checks the accepted daemon and image, obtains the PostgreSQL and n8n image IDs by read-only container metadata, and builds only a networkless staging-service overlay. It refuses an existing complete project. Its only application project is dincharya-stage1-complete. Preserve original and recheck containers, volumes and state. The restore helper removes only its own transient networkless verification container. The final trap stops the five new services and compares inventories for both earlier projects.

Wait through the real due minutes and the controlled service outage. Capture PASS lines, sanitized counters, journey/stop exit codes and inventory comparison. A first failure ends the run. Preserve the stopped project for investigation; do not replay decisions, delete volumes or proceed to Windows or Telegram acceptance. Record full runtime success only after both exit codes are zero and the script itself exits zero.
