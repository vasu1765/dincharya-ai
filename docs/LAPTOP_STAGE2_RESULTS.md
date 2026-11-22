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
