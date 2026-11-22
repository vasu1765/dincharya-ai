#!/usr/bin/env bash
set -euo pipefail
: "${REV:?reviewed clean revision}" "${PY:?pinned Python}" "${KERNEL:?verified public kernel}"
export DINCHARYA_STAGE2_RECOVERY_ONLY=1 PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
exec "$PY" -B staging/laptop/recovery_only.py "$@"
