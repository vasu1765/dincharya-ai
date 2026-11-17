# Cycle 7 supervised private Telegram acceptance proposal

**Approval required before starting.** Propose one session with the dedicated
`dincharya_acceptance_test_bot`, one owner-only private Telegram chat, fresh
disposable PostgreSQL and isolated n8n. The previous single-message M2G approval
is complete. Owner approval for this proposal must identify draft revision,
dedicated bot and private recipient by secure local configuration, test window,
and the six-message outbound cap. Approval of this document for review alone
does not authorize a send.

## Fixed scope

Agree a start minute T0 on a dedicated test date in Asia/Kolkata. Use a daytime
window ending by 21:00 IST. Enter the same civil date in both commands. The silent
appointment is T0 + 6 minutes and the reminding appointment is T0 + 8 minutes.
Confirm both by T0 + 4 minutes. If the window is missed, abort and agree a new
window under the approved scope before repeating any user interaction.

| Owner action | Exact requested scenario | Expected bot messages |
| --- | --- | --- |
| Ask one read-only question | `/panchang 6 December 2023` | One answer. No new event or request. |
| Submit and confirm one silent civil appointment | `Schedule Acceptance silent on YYYY-MM-DD at HH:MM; none` | One preview and one confirmation. Zero reminder slots, attempts or receipts. |
| Submit and confirm one reminding civil appointment | `Schedule Acceptance reminder on YYYY-MM-DD at HH:MM; at start` | One preview and one confirmation. One genuine reminder at the approved minute. |

Total outbound chat messages are capped at **six**, of which **one is a reminder**.
The scheduled reminder generates exactly one delivery attempt and one paired
chat/message receipt. Telegram callback acknowledgements are API responses, with
no separate chat message expected. Repeat worker ticks at least twice after the
receipt and inspect the ledger without sending extra chat commands. The owner
confirms on their device that one reminder arrived and the silent one produced
none. No birth or marriage examples, lunar projections, or live replay are in
this scope.

## Before approving execution

1. Complete the Cycle 7 exact-schema check and record the reviewed revision.
2. Prepare and review a bounded runner derived from the existing test-bot
   identity check. Pin the owner ID and bot ID, require explicit execution gates,
   keep only the two allowed titles and times, verify the isolated signed relay,
   and enable a single worker for at most one live send attempt. The development
   slot worker current entry point accepts injected transport for simulation.
   The bounded live wrapper needs separate implementation review before this plan
   is executable. Validate the wrapper against recorded IO first.
3. Take credentials from an owner-only local file via the existing protected
   launcher. Keep token, chat and message IDs outside logs and Git. Confirm no
   other poller or worker owns the disposable session. Record fixed preflight
   headings, Git revision and start window only.

## Stop and evidence

Stop on mismatch of bot identity, owner/chat, branch revision, database,
approval, schedule, counts, receipt or worker lock. Stop on any response with
uncertain acceptance, rejection, rate limit, unexpected message or second
attempt. Do not retry, clear a quarantine row or switch transports. Observe
through T0 + 11 minutes for the negative and duplicate cases. Stop gateway and
worker, revoke test credentials loaded into the process, and tear down this
session's database, n8n and local scratch files. Preserve only sanitized counts,
paired receipt present/absent, owner confirmation, cleanup result and the
pass/fail headings. Check unrelated processes and services are unchanged.
