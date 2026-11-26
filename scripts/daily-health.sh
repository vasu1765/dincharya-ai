#!/usr/bin/env bash
set -euo pipefail
# Run within the approved database container over its local socket.
exec psql -XqAt -v ON_ERROR_STOP=1 -U personal_observer -d dincharya_personal_candidate -c 'SELECT row_to_json(h) FROM beta.health() h'
