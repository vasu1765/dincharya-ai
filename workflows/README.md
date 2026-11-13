# Workflow source

No production workflow export is present. Only independently reviewed, sanitized
source may eventually enter this directory. Preparation writes private candidates
outside Git; there is no automatic promotion. Raw inputs, original workflow IDs,
version/publication metadata and credential-reference mappings stay private.

Candidates preserve connections/expressions, remove only credential references
into private mappings, and force active=false. Embedded IDs/literals remain
private pending review. They are not guaranteed n8n-importable. Inactive JSON is
not a sandbox. Version-specific import/execution tests require separately approved
isolated n8n. Current raw rows do not prove the published version's behavior.

## Repository-owned M2G acceptance template

m2g-lunar-acceptance.json is a new inactive native Webhook/HTTP Request template.
It forwards the gateway’s signed envelope/header to the lunar service; no Code
node, credential value or schedule trigger. Test harness substitutes only the
private fixture URL/relay authentication at runtime. It is not an adoption/import
claim for historical private workflows or source state. G01–G04 exercise the
real n8n path; production/live activation still needs authorization. See
[results](../docs/M2G_TELEGRAM_RESULTS.md).
