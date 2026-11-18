# Laptop Stage 1 acceptance results

## Scope and checkout

Approved revision: `37db544a872676ae75e2cacfa32b92f5775f2d46` (draft PR #14).
The owner fetched that exact PR head as `development/pr14-laptop-staging` rather
than the initially named branch. The controller pins the revision, not the branch
name; the tested tree was clean. A pre-existing untracked shell-artifact file was
preserved outside Git without content inspection before the build. Application
source and accepted migrations were not changed.

Stage 1 allowed disposable synthetic integration only. No private schema,
production data, real bot credential or Telegram transport was used. The earlier
Cycle 7 exact-schema and private-bot results remain separately scoped.

**Overall: FAIL / incomplete.** Image build, synthetic initialization and five-service
startup passed. The first synthetic confirmation response failed its assertion
after the database had committed the silent appointment. The remaining runtime
sequence was stopped, not credited. Staging was gracefully stopped and preserved.

## Verified official Python base

The owner separately authorized official Docker Library Python 3.12 base-image
selection. Registry discovery used `docker.io/library/python:3.12-slim-bookworm`;
the mutable tag was used only to discover the immutable reference.

- Official index: `sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df`.
- Selected platform: **linux/amd64**.
- Pulled and used as `BASE`:
  `docker.io/library/python@sha256:0f086103b026048cc50cb5da25ec435c023c5241a83fc44daea593377abc61c4`.
- Official registry annotations identify
  `https://github.com/docker-library/python.git#3d7e95597e56a415d9e4abc0f15877e005d2cb2e:3.12/slim-bookworm`
  and `https://hub.docker.com/_/python`. The daemon reported no registry mirrors.
- A networkless, read-only disposable container verified **Python 3.12.16**,
  **pip 25.0.1**, **OpenSSL 3.0.22**, loadable `libssl.so.3`, and the exact pinned
  Asia/Kolkata TZif digest from repository metadata.
- The unchanged Imagefile built from the runbook's explicit `git archive` paths,
  using only that digest. Both environment dependency checks passed. The separate
  application environment retained the astronomy certifi pin while the gateway
  retained its SDK pin. No mutable-tag fallback was used.
- Built local application image ID:
  `sha256:fff0b1b58321339ad0de04804548cb8ff14c9a929e6eead08ce3cd96535493ca`.
  A second networkless container instantiated the pinned astronomy runtime with
  the public DE440s and imported psycopg successfully.

## Acceptance matrix

| Acceptance item | Status | Actual evidence / limit |
| --- | --- | --- |
| Exact Git revision and clean tree | PASS | Approved full SHA; owner-selected PR branch alias noted above. |
| Approved Docker Desktop identity | PASS | `44c1ef83-c50e-4ecc-8f19-4b112bc40f29`. |
| Existing PG17 and n8n images | PASS | Original full local image IDs reused; no replacement of accepted images. |
| Host Python and public kernel | PASS | Existing pinned environment; all astronomy dependency versions and DE440s checksum matched metadata. |
| Conflicting staging resources | PASS | No staging state directory, containers, volumes or network existed before preparation. |
| Unrelated resource inventory | PASS | Two original running containers and two original volumes inventoried without opening data. Final unrelated inventories matched. |
| Application image build | PASS | Reviewed tracked-file context, verified official base digest, both pip checks, networkless astronomy smoke check. |
| Synthetic schema initialization | PASS | Repository-owned invented schema and migrations 0001–0014 initialized by the unchanged controller. No private baseline. |
| Five-service Compose startup | PASS | Database, native relay, application, offline gateway and single worker all healthy. |
| Network / mount isolation | PASS | Only the dedicated internal network, no published ports, no privileged service or Docker socket mount. Database TCP disabled. |
| PostgreSQL and n8n readiness | PASS | Health checks and signed application status succeeded. Actual pinned PG tooling is 17.11; n8n is 2.47.3. Work's separate 17.12 evidence is not substituted. |
| Signed relay authentication | PASS | Valid health request succeeded; altered signature returned denial. |
| Synthetic gateway authorization and preview | PASS | Foreign synthetic user ignored; owner preview returned; preview created no event. |
| Explicit civil approval persistence | PASS, bounded | One event, one recurring control and one approval audit record persisted for the first silent fixture. |
| SDK confirmation response | FAIL | The returned messages did not satisfy the single `Rule approved. ID ...` response assertion. The response was not logged. No approval was replayed. |
| Notification-policy ledger | NOT TESTED | Full four-fixture policy assertion sequence was not reached. Last observed totals: zero slots and zero attempts. |
| Silent delivery suppression | NOT TESTED | No attempt observed, but the timed negative check was not completed; do not claim silent scheduling acceptance. |
| Simulated reminder and paired receipts | NOT TESTED | No reminding fixture was approved; no receipt acceptance credited. |
| Runtime duplicate suppression | NOT TESTED | Sequence stopped before repeated approval/worker checks. |
| Runtime uncertain quarantine / no resend | NOT TESTED | Uncertain fixture was not submitted. Focused recorder unit coverage passed separately. |
| Single-worker topology / heartbeat | PASS | One healthy worker started. |
| Competing worker denial | NOT TESTED | Competing-worker probe was not reached. |
| Application / worker runtime restart | NOT TESTED | Controlled restart stages were not reached. No automatic rerun/reset was performed. |
| Recorder process persistence | PASS, unit only | Existing focused test reopened SQLite in a separate process and preserved receipt ordering; uncertainty remained terminal in its injected repository. |
| Missing-service health | PASS, bounded | Controller status returned failure after all services were stopped; live-outage recovery not tested. |
| Observer synthetic outage | PASS, unit only | Existing test classified successive missed samples as miss/outage and subsequent quarantine as attention. |
| Actual remote observer / outage transport | NOT TESTED | No approved external SSH observer configured or contacted. |
| Backup tool prerequisites | PASS | Host OpenSSL 3.0.13 and findmnt present; pinned image provides pg_dump and pg_restore 17.11. |
| Certificate pin and encryption integrity | PASS, synthetic unit only | Temporary RSA certificate; DER pin check; AES-256-GCM CMS round-trip; wrong pin and truncated archive rejected. |
| SQL restore and off-host backup | NOT TESTED | No staging dump or restore executed. No external destination, off-host certificate/key custody or recovery-host acceptance claimed. |
| Graceful stop | PASS | All five staging containers exited 0; no staging service remains running. |
| Preservation / unrelated resources | PASS | All four staging volumes and stopped containers retained for inspection. Original unrelated containers and volumes unchanged. Nothing shared deleted. |
| Windows power, lid, reboot and startup tasks | NOT TESTED | Outside Stage 1 authorization; no Windows changes or task registration performed. |
| GPU / optional model and physical rehearsal | NOT TESTED | No model invocation, lid closure or 30-minute rehearsal performed. |

## Focused evidence and failure review

`OPENBLAS_NUM_THREADS=1 /tmp/dincharya-m2g-runtime/bin/python -B staging/laptop/test_stage.py -v`
passed **five tests**. All six staging Python sources passed AST parsing; explicit
source scanning passed for those sources and the existing staging runbook. The
Imagefile was manually reviewed; no PowerShell execution or acceptance is claimed.

A separate synthetic Stage 1 harness used the actual offline SDK gateway, signed
native n8n relay and scoped application/database. It was held outside Git so the
approved clean-checkout gate remained intact. It exited **1** at the first
confirmation-response assertion. The first fixture's schedule/control/audit counts
were **1/1/1**, with **0 notification slots / 0 delivery attempts** at inspection.
This is a post-commit response uncertainty, not evidence that approval was rejected.
Do not create a replacement approval, reset history or rerun partially initialized
state to manufacture success.

One networkless offline SDK reproduction extracted the unchanged staging `Wire`
class and injected a stubbed successful approval response. It produced one
approval call and one approved reply, with zero fallback replies or handler errors.
That narrows the issue but does not identify a confirmed application defect.

### Smallest proposed correction for review

Add fixed, sanitized confirmation diagnostics to the staging journey before a
reviewed rerun: reply count, approved-reply count, fallback-reply count, keyboard
presence, and a post-decision aggregate persistence check. Do not print the reply,
review ticket, control ID, exception details or configuration. Preserve the
original assertion; a persisted event alone must not turn an unconfirmed response
into a pass. Add an offline regression covering an approval that commits but whose
confirmation response is missing or unexpected. Choose any subsequent application
fix only after those diagnostics establish its cause. No such source correction
has been applied to the approved revision in this run.

The project remains **stopped, with state preserved**. Do not reuse or remove this
partially initialized state without a separately reviewed disposable cleanup scope.
Stage 2 physical testing, persistent installation and any real Telegram test still
require their own authorization.
