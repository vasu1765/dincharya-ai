# Laptop-first personal beta

Stage 1's six WSL integration checks passed. Stage 2's preserved closed-lid evidence,
approved recovery-only run, owner-mediated encrypted USB transfer, independent PG17
restore and scoped cleanup are complete; see [actual results](LAPTOP_STAGE2_RESULTS.md).
Retain two exceptions: the observer ended before final fixtures (later verified through
SQL/recorder/restart), and the owner accepted a USB filesystem repair warning despite
matching transfer/restore integrity checks. SMB transfer was deferred, not accepted.

The shortest next step is PR-stack review and a separately approved bounded attended
personal beta on the AC-powered Acer, with a named revision, dedicated bot/private
recipient, secure local secrets, permitted activities/message limits, backup plan and
stop/rollback conditions. Start manually after interactive login; no startup task is
needed for this first bounded phase. Do not reuse acceptance databases as a personal
schedule. Existing private Telegram evidence does not authorize new sends. PR #16
stays draft; its reported mergeability must be reviewed before any merge approval.

Unattended operation remains gated on independently powered observation/owner alerting
and approved routine encrypted backups/recovery. Use healthy backup media rather than
treating the accepted one-off USB warning as a future storage policy. India VPS handover
is later and separately approved. No production, live lunar scheduling or personal
persistent deployment is authorized by synthetic acceptance alone.

## Host contract

| Component | Laptop | India VPS |
|---|---|---|
| Docker | One Docker Desktop WSL2 engine, integrated with the approved distro. Check Docker context and daemon ID before starting. | One Linux Engine. Verify the expected host, daemon and project before startup. |
| Startup | Proposed owner-login task starts the chosen distro and waits for Docker Desktop login startup. Use bounded readiness retries and a visible failure exit. Keep automatic login disabled. A reboot before login is a documented outage. | After separate deployment approval use an OS service with the same readiness gate, bounded restarts and stop timeout. |
| Application | Pin identical gateway, n8n relay, scheduler, worker, PostgreSQL 17 and model versions on both targets. Keep signed endpoints, role separation, Asia/Kolkata scheduling and UTC receipts. | Change host bindings, volume paths and local secret references only. Default all outbound activity off on a replacement. |
| Storage | Named Linux volume for PostgreSQL. Preserve relay state and signing configuration separately with restricted access. | Restore into fresh named volumes. Never start from a copied running database directory. |
| Ollama | Optional local NVIDIA backend. Probe with a benign inference and inspect model residency with ollama ps. | Same local API, with CPU fallback if measured latency is acceptable. Model failure must leave deterministic scheduling and existing reminders intact. |

Use a single supervisor per host. Start database first, verify schema and role access, then signed relay and gateway, then worker and polling after identity, destination and active-host checks. Keep administration ports on loopback or private container networks. For graceful stop, cease polling and new claims, drain in-flight work within the stop timeout, then stop worker, application and database. Preserve delivery attempts across every stop. An interrupted send with unknown outcome stays quarantined.

## Power, visibility and recovery

Read-only Windows preflight: record the active scheme with `powercfg /getactivescheme`, supported sleep states with `powercfg /a`, and effective AC/DC lid, standby and hibernate values with `powercfg /query`. Check managed policy and OEM overrides. After separate approval, target AC lid action “Do nothing” with idle sleep and idle hibernation disabled on AC. Keep thermal and critical-battery protections. Use a ventilated powered location. Stop the trial on AC loss. Locking Windows must preserve the session. After a reboot an owner must log in before the proposed login task can recover the stack.

Sample outside WSL every 15 seconds from a second device during acceptance. Record UTC time, Windows boot and login, Docker availability, DB read/write canary in a disposable schema, signed relay readiness, worker heartbeat/lock, oldest due slot, retry count and quarantine count. Use restricted read-only status or attended observation, with no public admin endpoint. Alert the attending owner locally on two missed samples, overdue backlog beyond the configured lookback, repeated startup failures or any quarantine. A laptop cannot report its own complete outage: unattended beta requires an independently powered monitor with an approved owner-visible channel. Exercise that alert with Telegram egress blocked. Keep identifiers and payloads out of evidence.

Schedule encrypted off-host logical backups at least daily for the beta; proposed recovery targets are 24 hours of data loss maximum and restoration within two hours. Record database/schema version, role definitions, artifact checksums and time. Keep secrets separately protected. Test restore into a second isolated cluster, recreate scoped roles, fence partial approvals using [the recovery procedure](M2H_CYCLE7_RECOVERY.md), and compare rules, slots, receipts and quarantine. A stale backup can omit an already accepted send: hold delivery across the entire uncertain interval pending owner reconciliation. A successful dump alone cannot qualify recovery.

## Preventing two active hosts

Use cold handover with manual fencing. Issue polling credentials only to the active host. An inactive host has no bot credential, worker startup authority or Telegram egress. A database advisory lock protects workers sharing that database only. Before migration stop the old poller, relay, scheduler and worker, disable their restart and outbound access, drain or quarantine in-flight sends, then take the final consistent backup. Verify the source remains fenced across reboot. Rotate bot credentials before giving the destination sole access; revoke old database and signing access. Verify the old host cannot poll or claim before allowing a destination poller. If either host's authority or ledger continuity cannot be established, keep both stopped. Never use Telegram polling conflicts as leader election. No automatic laptop/VPS failover is proposed.

## Supervised physical acceptance (simulation first)

Use a disposable database, synthetic authenticated owner and Telegram recorder reachable only inside the isolated test network. Deny external Telegram egress. The recorder must retain accepted message identities across the controlled restart. Preapprove synthetic civil events through the application. Use the revision's configured catch-up lookback; choose the reboot slot due time so measured recovery falls inside it. Keep an additional synthetic slot older than that window. Record actual times and classify a missed timing condition as inconclusive.

| Phase | Action | Required observation |
|---|---|---|
| Baseline | Verify expected host and sole worker/poller, AC state and backup. Exercise a silent event. | Healthy status and zero silent attempts. |
| Closed lid | Lock Windows, close lid on AC for 30 minutes. Schedule two distinct at-start reminders at +5 and +20 minutes. | External samples continuous, no OS sleep/hibernate events, one recorded receipt per slot. |
| Reboot | Open lid, gracefully stop and reboot under supervision. Delay login briefly, then log in; close lid again after startup. Place a third slot in the bounded outage and a fourth after readiness. | Independent monitor signals outage and recovery. Volumes, receipts and pending work survive. Third and fourth slots each have one receipt; older slot is withheld. |
| Faults | Simulate lost send response for a fifth slot, repeat worker ticks, attempt second worker against same test database. Try starting the fenced standby without credentials. | Exactly one uncertain attempt, no repeat, four accepted slot receipts, zero extra sends, one polling owner. |
| Restore and finish | Restore disposable backup with polling and sending fenced. Inspect ledger and roles, then stop temporary processes and remove only verified test resources. | No replay. Owner receives a sanitized result with heartbeat gaps, restart duration, receipt counts, stale and quarantined counts, and restore duration. |

Stop immediately for wrong identity, live egress, second active poller/worker, unexpected delivery, lost evidence, thermal/power concerns or unauthorized state. A later real-message test requires a new named bot, owner destination, revision, schedule, message cap and stop conditions. Host settings, login startup registration, persistent installation and reboot each require specific approval before execution.

References: [Microsoft lid policy](https://learn.microsoft.com/en-us/windows-hardware/customize/power-settings/power-button-and-lid-settings-lid-switch-close-action), [Docker Desktop login settings](https://docs.docker.com/desktop/settings-and-maintenance/settings/), [Ollama Docker GPU options](https://docs.ollama.com/docker).
