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
