# Stage 2 attended run — 22 November 2026

Approved application revision: `fb023f11244a6b116c7ae1d17cb3b3c8cce9e6a7`.
Overall: **INCOMPLETE / recovery acceptance failed: missed bounded login/recovery window.**
No delivery history reset, phase replay or automatic resend.

| Check | Verified result |
| --- | --- |
| Clean approved checkout, pinned daemon and current signed health | PASS before arming; all delivery counts zero |
| AC lid, standby and hibernation settings | PASS fresh read-only checks |
| Independent observer initial readiness | Owner reported three consecutive healthy samples and fresh timestamps; complete log not yet inspected |
| Arm and closed checkpoints | PASS; arm completed 05:31:09 UTC, closed checkpoint 05:31:20 UTC |
| Open checkpoint | PASS at 06:02:58 UTC: elapsed interval, AC, no detected sleep event and unchanged boot; actual physical close/open times and complete observer evidence still required |
| Initial delivery receipts and interruption | PASS: two paired receipts verified; Stage 2 stopped at 06:03:15 UTC |
| Supervised reboot and bounded recovery | NOT ACCEPTED: owner-side guard rejected timing; at 06:13:10 UTC the 06:06:00 due time was already 430 seconds past. No recover.started or recover.done exists; reboot evidence not independently checked after restart |
| Four receipts, zero silent attempts, one uncertain, single-worker final verification | NOT TESTED for final acceptance; verify was never run |
| Abort and prior inventories | PASS: documented stop exited 0, aborted marker persisted; prior three Stage 1 project inventories matched saved baseline |
| SMB transfer/isolation | NOT TESTED / DEFERRED; receiver metadata matched configured scope, but no encrypted connection or independent negative-source test was performed |
| USB amendment | Prepared outside Git; guarded local encrypted-export companion syntax and denied-entry checks passed. No export or USB transfer executed |
| Independent PostgreSQL restore | NOT TESTED in this Stage 2 run |
| Temporary monitoring/SMB cleanup | PENDING scoped review; no unrelated rules, shares or services removed |

All Stage 2 state, phase journal, database volumes and receipt history remain preserved.
Do not run recover, verify or export against this aborted session. Do not repeat any
approval. A fresh physical attempt and another reboot require new owner authorization
and reviewed handling of the preserved aborted project. Existing Stage 1 evidence stands.

Owner should stop the ThinkPad observer with Ctrl+C and retain its complete sanitized
JSONL. Record actual physical lid-close/open times and login/reboot timing for diagnosis.
No real Telegram, production access, deployment, automatic startup or main merge.


## Approved recovery-only continuation — 22 November 2026

Application checkpoint `b89a2bc4bf7de64889899f79935edafe986d9156`; fresh isolated
recovery-only project. No original physical session phase/state was reset or resumed.
The prior successful lid/initial receipt evidence is retained; no repeated lid test.

| Check | Actual result |
| --- | --- |
| Fresh synthetic initialization and separate namespace | PASS; no fixtures until independent readiness/attendance |
| One additional supervised reboot and manual recovery | PASS; changed boot and stopped-state checks passed |
| Stop-to-signed-ready performance | PASS: 435.014 seconds (7m15s), target 600 seconds |
| Genuine overdue catch-up | PASS: two paired reminders, first receipt 411.416 seconds after stop; overdue ages 301.253 and 243.064 seconds; no due-date rewrites |
| Pre-outage history | PASS: immutable pre-outage history and recorder receipt preserved |
| Final delivery outcomes | PASS: four paired sent receipts, one uncertain attempt without receipt/resend, zero silent and legacy delivery work |
| Duplicates and competing worker | PASS: subsequent ticks plus controlled app/worker restart preserved history and attempts; competing worker rejected; one advisory-lock owner |
| Independent outage/recovery trace | PASS under unchanged continuation verifier: 66 samples, largest gap 18.98 seconds, correct project/revision, pre-arm health, outage and recovered readiness |
| Observer tail | LIMITATION: log ends 08:21:43 UTC / 13:51:43 IST, before the final reminder and uncertain fixture. Later outcomes are verified by SQL/recorder and controlled restart, not by continuous external monitoring through the end |
| ThinkPad observer/Docker crash cause | UNCONFIRMED: owner reported observer termination and a possible Docker crash; no causal claim or recovery-host acceptance inferred |
| CMS encrypted local export and manifest | PASS: one-use encrypted publication, six history hashes, no plaintext dump; export/source task exit 0 |
| Scoped source stop and original inventories | PASS: recovery-only services stopped; all prior stopped project inventories and aborted journal fingerprints unchanged |
| USB transfer and independent ThinkPad restore | PENDING; no files transferred by the assistant |
| SMB isolation/transfer | NOT TESTED / DEFERRED; no mounting or additional SMB configuration |
| Temporary receiver/monitor cleanup | PENDING reviewed exact-resource cleanup |

The private monitoring bridge had a demonstrated Windows PowerShell null-binding defect:
`File.Replace(source,target,$null)` failed with ArgumentException. Synthetic red-before-fix
reproduction and explicit NullString correction passed. Fixed reader/publisher diagnostics
preserve the original scripts, all authorization/schema/freshness checks and failed-health
cache removal. Eight synthetic reader cases passed; 15 real cache samples across five
publications had zero failures after correction. No application/source revision changed
for this private operational bridge correction; no SSH/firewall permissions were relaxed.

**Source functional recovery, performance and encrypted export PASS. Overall Stage 2
closeout remains pending independent USB restore and documented cleanup.** The observer
termination is a retained limitation, not erased or attributed to Docker without evidence.
No further physical test is proposed by this report. Preserve both sessions and all logs.


### USB copy checkpoint

Owner explicitly instructed proceeding despite a read-only preflight reporting USB
volume health Warning / Full Repair Needed. This exception is retained; filesystem
health is NOT PASSED. Only the CMS ciphertext and restore-manifest were copied to the
owner-named empty USB folder, without overwrite; both source/destination SHA-256 checks
passed and exactly two files were present. Copy exit 0. Acer originals preserved;
no filesystem repair/format or plaintext/key/config transfer. Safe ejection, receipt on
ThinkPad, repeat integrity verification and independent restore remain pending.


### Independent restore and final source inventory

Owner-executed ThinkPad task reported: expected clean revision, pinned independent
daemon/PG17 and local recipient key/certificate PASS; USB and copied destination hashes
PASS; restore exit **0**; migration checksums and all six histories match; slots=5,
sent=4, uncertain=1; no application/worker started and transient restore container removed.
This is owner-returned sanitized runtime evidence, not an assistant-side connection to
ThinkPad. No plaintext/key was transferred. The accepted USB repair warning remains.

Final assistant read-only Acer checks PASS: recovery-only stack stopped; export complete;
all earlier project inventories and original aborted journal fingerprints unchanged.
Attended status bridge and exact Stage 2-configured SSH service were stopped after
checking the saved original service state was Stopped; no TCP 22222 listener remains.
Accounts, firewall rules, receiver configuration and evidence have not been deleted.

**Recovery-only functional, startup-performance, encrypted-transfer integrity and
independent-restore acceptance PASS, with the observer-tail limitation and owner-accepted
USB filesystem warning explicitly retained.** No repeated lid test is required by this
result. Original aborted recovery is not retroactively passed. Remaining operational
closeout: reviewed removal/restoration of temporary receiver/monitor configuration and
commit/push of these two evidence documents. No production/persistent deployment or
release approval follows from this acceptance.


### Final scoped cleanup — Acer verified; ThinkPad local execution pending

At evidence commit a2acdd4, owner authorized exact-resource cleanup. Acer preflight
matched saved original SSH service state, temporary account SID against setup ACL,
and both exact firewall endpoint/source scopes. Cleanup exited 0: restored original
SSH binary/configuration and Manual/Stopped state; removed temporary monitor account
and exact two monitoring rules; verified no test listener and unchanged unrelated
firewall rule inventory. Monitoring configuration retired offline with diagnostics;
all databases, Docker/WSL installations, journals, archives and evidence preserved.
ThinkPad receiver account/share/rules cleanup requires owner-local execution and is
not yet claimed. Observer-tail and USB filesystem exceptions remain unchanged.


### Final closeout — ThinkPad owner-confirmed cleanup

Owner returned the local guarded cleanup results: PASS temporary account/share/two
firewall rules removed; PASS original destination permissions restored and unrelated
rules unchanged; PASS archives, keys, restore records and recovery directory preserved.
The task matched the account SID and exact share/firewall scopes before removal.
This is owner-executed evidence; no remote administrative access to ThinkPad was used.
Together with verified Acer cleanup above, final scoped cleanup is complete. Earlier
pending cleanup statements are chronological checkpoints superseded by this section.

No Stage 1/Stage 2 database, volume, journal, receipt, observer log, encrypted archive
or independent restore record was deleted or reset. Retired monitoring source/config
and diagnostics remain offline evidence; active monitor account/rules/service target
were removed/restored. USB repair warning and missing external observation of the late
fixtures remain explicit. SMB isolation was not tested and is not credited. No claim
that the observer crash was caused by Docker. No physical retest is required solely
because of the retained tail gap under the approved continuation criteria.

Approved Stage 2 acceptance/cleanup has no remaining execution gate. This does not close
all Milestone 2 release requirements: PR-stack review (PR #16 remains draft and GitHub
reported not mergeable at closeout), source-adoption and broader calendar decisions,
and separately approved personal operation remain. Unattended operation still needs
independent monitoring/alerts and routine backup arrangements. No real Telegram,
persistent deployment, automatic startup or main merge has been enabled.
