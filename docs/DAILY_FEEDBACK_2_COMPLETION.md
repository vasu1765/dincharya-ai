# Feedback Release 2 completion gates

The previously accepted runtime was `dcd0e40`. Carry forward its 46 Python
tests, 37 checksum entries, PostgreSQL approval and rollback acceptance,
and disposable cleanup. The completion task runs only the new benchmark
protocol tests, calendar coverage and schema delta.

## Model qualification

The original Acer run used Ollama's native JSON-schema `format`, temperature
zero, 2,048 context tokens, a 256-token output limit and one inference at a
time. It scored responses by parsing them through the production validator.
The harness reported generic interpretation failures, so that run cannot
distinguish JSON, omitted schema fields, bad dates/times or incorrect intent.
It retained no raw completions. The all-required schema forced eight keys
even when a clarification needed just an action. It mixed parse, schema and
semantic failures in one count. The prompt specified policy but had no
worked multilingual examples. The lone multi-turn sample used a partial
context object. These are plausible causes to test, with no attribution to
the model based on the aggregate alone.

The new protocol alternates the existing transport shape and a compact
shape with multilingual examples. Both send Ollama native `format` with
additional fields forbidden. The compact shape permits omitted unused
fields. All proposals still enter the unchanged production validator.
The benchmark logs transport, JSON, shape, validator and semantic mismatch
counts separately. The same 16 invented cases cover English, Hindi and
Hinglish, active and passive voice, relative and ordinal dates, explicit
times, recipient/location scope, contextual and context-free follow-ups,
ambiguity and injection. The fixture compares title, timing and recurrence
where each is essential. It also samples host RAM/VRAM, reads per-model
offload bytes from Ollama, captures cold/warm durations and token counts,
and measures synthetic reminder jitter without using the active ledger.
Run the three digest-pinned models sequentially on the dedicated loopback
listener and temporary public model store. Require 3,072 MiB available
before startup or loading another model and abort model work below 1,536
MiB during evaluation. Run the benchmark independently of other resource
tests.
[Ollama native structured-output API](https://docs.ollama.com/capabilities/structured-outputs)

The previous 3B baseline was 4/10 accepted by the validator and 3/10
semantically matching, 4.94 s cold and 0.77–1.19 s warm. The model was fully
offloaded and the sampled free RAM floor fell to 394 MiB. The earlier 7B
attempt stopped during download when memory was low. Qwen3 4B was not
inferred. This checkpoint initially measured 2,194 MiB free on Acer, below
the admission floor. A meaningful model selection requires paired evidence
with the revised protocol. The deterministic path remains the interim
fallback. The provider-neutral architecture and cloud opt-in stay as
approved.

## Closed-lid reliability

Windows power-source event 105 recorded AC offline at 09:35:54 UTC on
28 November 2026. It was still the last recorded source state for sleeps
at 10:47:47, 11:01:34 and 11:12:36 UTC. The first and third had a
button-or-lid reason. The current plan shows AC lid action 0, DC action 1,
AC sleep and hibernate timeouts zero, DC sleep 600 seconds and DC hibernate
10,800 seconds. The last query showed AC online. AC settings apply only
while Windows reports AC. The DC policy explains the lid sleeps during the
observed battery interval. The older ReadTimeout still has no timestamped
request phase that identifies a particular sleep as its cause.
[Microsoft lid action indices](https://learn.microsoft.com/en-us/windows-hardware/customize/power-settings/power-button-and-lid-settings-lid-switch-close-action)

Keep the approved AC policy and battery protections. The minimal operational
correction is to secure the charger and require Windows to report AC before
closing the lid. If power source is uncertain, leave the lid open. An
attended 60-second observation is pending. In a quiet window, with the
owner present on AC, run
`python3 -B tests/acer_lid_observe.py --owner-attending` from the clean
candidate. Close after the prompt, reopen after one minute, then allow the
90-second disposable Docker heartbeat to finish. The check combines Windows
sleep/source events with wall-clock heartbeat gaps. It starts no application
or database and leaves appliance settings untouched. Stop on loss of AC
or unexpected sleep. Read-only retry and outbound quarantine already passed
the prior candidate tests. This physical observation checks uninterrupted
host/runtime availability rather than re-running delivery acceptance.
A DC policy change would require a separate owner decision.

## Delhi annual coverage

New Delhi daily pages publish ordinary Margashirsha Krishna Dashami under
Purnimanta on these dates. The reviewed calculator must also produce one
civil sunrise choice and a distinct logical lunation identity for each
year. The sources are independent of the application calculator.

| Year | Delhi Purnimanta date | Publisher |
| --- | --- | --- |
| 2026 | 3 December | [Drik Panchang](https://www.drikpanchang.com/panchang/day-panchang.html?date=03%2F12%2F2026) |
| 2027 | 23 November | [Drik Panchang](https://www.drikpanchang.com/panchang/day-panchang.html?date=23%2F11%2F2027) |
| 2028 | 12 November | [Drik Panchang](https://www.drikpanchang.com/panchang/day-panchang.html?date=12%2F11%2F2028) |

The focused test starts with an invented historical event instant on the
public [14 November 2025 Delhi reference day](https://www.drikpanchang.com/panchang/day-panchang.html?date=14%2F11%2F2025)
and derives the annual Purnimanta rule. The cases include a historical
Adhika Shravana Shukla Dashami, an absent Adhika occurrence in a comparison
year, repeated Chaitra Shukla Dwadashi on consecutive dawns with
first/last/review policies, and a skipped Shravana Krishna Ekadashi dawn.
The 2023 corroboration is in the pinned PAC reference register, with a
direct [Delhi second-dawn comparison](https://www.drikpanchang.com/panchang/day-panchang.html?date=03%2F04%2F2023).
Historical exceptions exercise guards and policy without extending the
runtime scheduling allowlist. Future dates outside the three new rows and
the existing 2027 Amanta row remain withheld. The 2029 candidate was
computed but lacked a verified same-city daily source in this checkpoint.
Festival rules and Kshaya remain outside the release.

## Exact upgrade and rollback sequence

1. Wait for approval of the exact development revision and its release
   manifest. Verify the 37 carried checksums in the old revision and all
   expanded checksums in the candidate. Verify the approved PostgreSQL
   17 identity and volume. Use STOP and verify there are zero worker and
   gateway connections and both ownership locks are released.
2. Before changing anything, obtain separately authorized encrypted
   snapshot evidence. Record checksums and aggregate schedule, occurrence,
   slot, receipt, uncertainty and authority counts. Verify that the
   snapshot can be read and restored into a fenced disposable PG17 target.
3. With the operator stopped, and an explicitly approved personal
   database container ID, apply the following from the reviewed checkout
   using the database administrator on the approved local connection.
   Apply 0006 only if absent from the exact applied migration register.
   Apply 0007 once after 0006. Each migration owns its transaction.

   ```bash
   sql=(docker exec -i "$APPROVED_DB_ID" psql -Xq -v ON_ERROR_STOP=1
        -U postgres -d dincharya_personal_candidate)
   "${sql[@]}" < database/personal/0006_feedback.sql
   "${sql[@]}" < database/personal/0007_delhi_lunar_coverage.sql
   ```

4. Recheck hash register, aggregate counts, migration 0007's three
   independent references, scoped privileges, locks and STOP. Bind a
   fresh owner-approved release. Keep provider configuration absent until
   the separately qualified local model is approved.
5. For rollback before any new accepted actions or deliveries, restore
   the independently verified pre-upgrade snapshot to the fenced target
   and require fresh authority. After any new actions, stop both owners
   and preserve a new encrypted snapshot and all history. Use the tested
   `scripts/daily-feedback-compat.sql` against the stopped, verified
   0006/0007 target to restore the legacy list cap and disable further
   lunar projection. It leaves existing schedules, slots, receipts,
   evidence and model reservations in place. Compare counts and confirm
   the old host is fenced before reviewing a compatible restart. Keep
   uncertain deliveries quarantined. Re-enabling candidate function
   definitions after compatibility rollback requires a separately
   reviewed migration step. Do not reapply 0006 or delete history.

## Focused rerun

Set `REV` to the clean candidate, and `KERNEL` and `CERTIFI_WHEEL` to
the pinned public assets. Run `bash tests/daily_feedback_delta.sh completion`.
The mature runtime's earlier tests carry forward. Only the new formatter,
calendar cases and additive SQL acceptance run on this path.

### Verified completion evidence

The clean tested delta `436473383525e11c31bc5c677a4a4c7a8a96f164` exited 0.
All 44 manifest records matched. Two benchmark contract tests passed.
The pinned astronomy child independently derived the historical event
rule, matched all three ordinary Purnimanta dates and distinguished their
logical identities. It also passed Adhika/ordinary separation, repeated
first/last and review, skipped withholding and out-of-coverage rejection.
Fresh networkless PG17 applied 0001–0007. The exact three new registry rows
matched, runtime write grants remained fenced, and no authority or
scheduling records were seeded. Disposable cleanup and Docker inventory
comparison passed. The prior 46 tests and rollback result carry forward.

The owner chose to leave the real three-model comparison and physical
lid test pending. No candidate model is selected. The AC/DC diagnosis and
attended procedure above are available for the next qualified window.
