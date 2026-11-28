# Daily-use Feedback Release 2

## Candidate scope

This is an isolated development release. The running personal release and its
database were left untouched. The earlier disposable audit evidence carries
forward. The personal upgrade uses migrations 0001–0005 as its baseline and
adds 0006 on the candidate target only.

- The existing signed gateway and PostgreSQL ownership locks govern
  execution. Exact slash commands, calendar calculations and approved drafts
  remain deterministic. An optional configured language provider handles
  other phrasing. Its schema has no action to approve, cancel, send, run SQL or
  modify existing records. The router translates validated proposals into
  existing preview commands, with confirmation and immutable receipts.
- The single-owner context holds one successful structured Panchang result and
  one pending intent for up to 15 minutes in memory. It holds no free-form
  conversation history and does not survive process restart. After restart,
  ask for the source date or event instant again. Pending PostgreSQL approval
  buttons still follow the existing origin and expiry checks.
- Today, tomorrow, yesterday, ordinal dates and day-first Indian numeric
  forms are resolved in Asia/Kolkata. Delhi Panchang gives Purnimanta Māsa
  first, Amanta second, with Paksha and Tithi at sunrise and at the requested
  instant when supplied. Uncertain fields are labelled. The 300-second
  sunrise guard, reference uncertainty and ephemeris remain in force.
- Use /today, /tomorrow, /upcoming, /status, /help and /panchang. Use /rules
  and /rules 2 through /rules 7 for up to 100 active rules. Each page emits
  one bounded Telegram message. Relative civil drafts support today,
  tomorrow, hours and minutes. Unsupported media receive a type-specific
  text reply and their file identifiers are unused.
- Lunar scheduling projects only a date backed by the reviewed evidence and
  the unchanged guarded calculator. The current positive entry is 2027
  Kartika Krishna Dashami under Amanta. Its ordinary month date passed
  both sunrise models. Out-of-coverage years, skipped tithis, unsupported
  Adhika/Kshaya cases and repeated dawns without an independently reviewed
  selection produce no appointment. The registered series stays lunar.
  Additional future dates need a reviewed additive evidence entry. A
  cancellation keeps historical appointment and delivery records. Changing
  an existing lunar rule requires a reviewed cancellation and a new preview.
  No festival tradition was selected.

## Retry and lid evidence

The old terminal error provided only ReadTimeout. The owner reported it
after successful signed relay operations. Windows logged three sleep/resume
pairs in the inspected time range and two sleeps attributed to a button or
lid event. The absent request phase and precise terminal timestamp prevent
linking one sleep to a particular Telegram call. No Windows power setting
was changed. A new candidate closed-lid/recovery observation still requires
an attended window that will not disrupt the running release.

Daily-mode reads use at most four attempts with short bounded backoff and
STOP/expiry checks around waits. Telegram getUpdates repeats the same
durable cursor. Sends, edits, callback answers, reminder operations and
signed relay requests keep the existing one-attempt path. Ambiguity and
unconfirmed receipts still fence the runtime. Diagnostics contain only the
known operation, timing and allowlisted exception category. Successful
ordinary polls do not generate per-poll logs.

## Provider activation and spending controls

Configure a protected mode-600 `llm.json` only after model approval.
The local Ollama profile pins the expected model name and published manifest
digest, and uses a loopback or approved Docker host endpoint. Start with
2,048 context tokens and one inference at a time. The model background thread
has only the HTTP provider. The operator thread continues its normal
reminder loop while awaiting one intent. Timeouts, mismatched model digests,
missing providers and malformed responses cannot execute a draft.

The OpenAI Responses adapter is an explicit alternative profile. It uses
strict structured output, limits input and output sizes, and keeps storage
disabled per request. A separate protected key and reviewed model rate
reserve are required. PostgreSQL atomically reserves the configured
worst-case per-call micro-USD estimate and count before an external call.
The first reservation fixes both caps for that release. Review conservative
rates before provisioning and set the provider project’s own billing limit.
The local adapter never selects OpenAI on failure. Hybrid routing stays
unconfigured pending a separate policy. No paid calls were made.
[Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
[OpenAI structured outputs](https://platform.openai.com/docs/guides/structured-outputs)

## Acer synthetic qualification

Ollama 0.40.19 ran on a separate Windows loopback listener with its own
temporary public model cache. Acer has 15.7 GiB RAM and an RTX 4050 with
6,141 MiB VRAM. Ten invented English, Hindi and Hinglish requests covered
active/passive phrasing, ordinal and relative dates, context, ambiguity and
injection.

| Model | Pinned manifest | Schema accepted / semantic match | Time and resources |
| --- | --- | --- | --- |
| Qwen2.5 3B | `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b` | 4/10 · 3/10 | Cold 4.94 s, warm 0.77–1.19 s. Model fully offloaded, about 2,095 MiB sampled GPU use. Free RAM fell from 1,997 MiB to 394 MiB. |
| Qwen2.5 7B Instruct Q4_K_M | `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` | Pending | Download interrupted before inference with only about 1.1 GiB available, to protect the live host. |
| Qwen3 4B | `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7` | Pending | Conditional comparison after a viable 7B run. |

The benchmark listener and its scratch store were cleaned up. Current
recommendation is to keep deterministic handling in daily operation. The
3B measured interpretation accuracy and RAM floor do not qualify it. A
guarded rerun of the larger models needs at least 3 GiB available RAM at
start and stops below a 1.5 GiB working reserve. The harness can measure a
synthetic reminder function tick during real inference without touching
the active worker. That measurement and actual lid operation on this build
are pending. The focused unit test shows that a blocked provider leaves the
operator thread available.
[Official Qwen2.5 7B Q4_K_M model](https://ollama.com/library/qwen2.5:7b-instruct-q4_K_M)

## Qualification and upgrade

On Acer from the reviewed clean candidate checkout, set `REV` to the exact candidate SHA, and set `KERNEL` and
`CERTIFI_WHEEL` to the two pinned public assets and run
`bash tests/daily_feedback_delta.sh`. The runner uses only the accepted
immutable images, no network, a fresh PG17 and invented fixtures. It checks
the changed calendar and provider paths, SQL role grants, review binding,
projection/slot uniqueness, cancellation, and the cloud reserve limit.
Verify the final cleanup marker.

For a later owner-approved upgrade, use STOP and verify both runtime locks
are released. Export an approved encrypted pre-upgrade snapshot and compare
the exact current schema and migration hashes. Apply only 0006 in one
transaction to the pinned personal PG17. Verify the original schedule and
delivery counts, role grants, and aggregate health before a new exact
release approval. Keep the provider configuration absent until separately
qualified. Enable the approved provider only under a reviewed runtime pin
and owner-approved configuration during the subsequent activation.

Rollback before any new actions may use the verified pre-upgrade snapshot
under the existing restore fence and fresh owner approval. Once new
appointments or deliveries exist, preserve the current data and receipts.
Stop the candidate and take a new encrypted snapshot. Apply the reviewed
`scripts/daily-feedback-compat.sql` only after both ownership connections
are released. It restores the legacy rule-list cap and disables new lunar
projection while retaining all lunar and receipt records. Review the
resulting count and role checks before resuming a compatible runtime. A
database restore must keep the old host fenced, invalidate stale approvals,
and preserve uncertain delivery without replay. Never restore an older
copy over later accepted deliveries.

### Accepted changed-path evidence

The clean runnable revision `dcd0e40bfd1ce326ccbd590aef48b9cdd81c7b37`
passed the focused native command, exit 0. All 37 release checksum entries
matched. The pinned app ran 37 focused transport, intent and UX tests plus
nine historical regressions in the separate astronomy child, with zero
skips. The actual DE440s sunrise/instant and guarded annual lookup passed.
A networkless PG17 applied 0001–0006 and checked owner scope, preview
receipt binding, the 100-rule cap, projection idempotency, approved lunar
cancellation and atomic cloud budget. The compatibility rollback kept
ledger counts and restored the legacy cap. Both fixtures were removed and
the Docker container, network, volume and image inventories matched.

The guarded remaining model check is
`python -B tests/benchmark_daily_intents.py` from this checkout with the
accepted host HTTPX interpreter. The benchmark harness verifies pinned
public model digests in its isolated loopback Ollama instance. A local
provider profile uses `provider=ollama` with fields `model`, `digest`,
`endpoint`, `timeout`, `max_calls`, `max_micro_usd` and
`per_call_micro_usd`. The three cloud budget values are zero for Ollama.
An OpenAI profile uses its fixed HTTPS API endpoint and reviewed positive
budget values, an empty model digest, and a separate protected key.
No provider file was installed on the active host runtime.
