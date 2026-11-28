#!/usr/bin/env bash
# Focused feedback candidate. Only local immutable images, synthetic data and networkless fixtures.
set -euo pipefail
umask 077
mode=${1:-feedback}
[[ "$mode" == feedback || "$mode" == completion ]]
[[ $(git rev-parse HEAD) == "${REV:?exact feedback candidate revision}" && -z $(git status --porcelain) ]]
sha256sum --quiet -c docs/daily-release.sha256
expected=44c1ef83-c50e-4ecc-8f19-4b112bc40f29
pg=sha256:ff87138949ad9a46f32ff23bd6852b52ce024a13dffe9b4087be98292cdd3b4f
app=sha256:fff0b1b58321339ad0de04804548cb8ff14c9a929e6eead08ce3cd96535493ca
[[ $(docker info --format '{{.ID}}') == "$expected" ]]
for image in "$pg" "$app"; do [[ $(docker image inspect --format '{{.Id}}' "$image") == "$image" ]]; done
kernel=${KERNEL:?pinned public DE440s}
wheel=${CERTIFI_WHEEL:?pinned public certifi wheel}
[[ "$kernel" == /* && "$wheel" == /* && -f "$kernel" && -f "$wheel" ]]
[[ $(sha256sum < "$kernel" | cut -d' ' -f1) == c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2 ]]
[[ $(sha256sum < "$wheel" | cut -d' ' -f1) == 0f212c2744a9bb6de0c56639a6f68afe01ecd92d91f14ae897c4fe7bbeeef0de ]]
tmp=$(mktemp -d)
mark=$(openssl rand -hex 12)
id=
stage=preflight
inventory() {
  docker ps -aq --no-trunc | sort
  docker volume ls -q | sort
  docker network ls -q --no-trunc | sort
  docker image ls --no-trunc --format '{{.ID}} {{.Repository}}:{{.Tag}}' | sort
}
inventory > "$tmp/before"
cleanup() {
  local rc=$?
  if [[ $rc != 0 ]]; then printf 'FAIL stage=%s exit=%s\n' "$stage" "$rc"; fi
  if [[ -n "$id" ]]; then
    if [[ $(docker inspect -f '{{index .Config.Labels "org.dincharya.feedback-fixture"}}' "$id") == "$mark" ]]; then
      docker rm -fv "$id" >/dev/null || { [[ $rc != 0 ]] || rc=1; }
    else
      [[ $rc != 0 ]] || rc=1
    fi
  fi
  if inventory > "$tmp/after" && cmp -s "$tmp/before" "$tmp/after"; then
    echo 'PASS disposable cleanup and unchanged Docker inventory'
  else
    echo 'FAIL disposable cleanup or Docker inventory'; [[ $rc != 0 ]] || rc=1
  fi
  rm -rf -- "$tmp"
  exit "$rc"
}
trap cleanup EXIT
stage=python_fixture
docker run --rm -i --network none --pull never --read-only --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m \
  --cap-drop ALL --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
  -v "$PWD":/repo:ro -v "$kernel":/fixtures/de440s.bsp:ro \
  -v "$wheel":/fixtures/certifi-2025.10.5-py3-none-any.whl:ro -w /repo \
  -e OPENBLAS_NUM_THREADS=1 -e PYTHONPATH=/repo -e DINCHARYA_PUBLIC_DE440S=/fixtures/de440s.bsp --entrypoint python "$app" -B - "$mode" <<'PY'
import subprocess, sys, unittest
from pathlib import Path
from dincharya.personal_history import lookup, anniversary
if sys.argv[1]=="completion":
    result=unittest.TextTestRunner(verbosity=1).run(
        unittest.defaultTestLoader.discover("tests",pattern="test_intent_benchmark_cases.py"))
    if not result.wasSuccessful() or result.skipped:
        raise SystemExit(1)
    subprocess.run([sys.executable,"-I","-S","-B","tests/daily_completion_astronomy.py",
                    "/fixtures/certifi-2025.10.5-py3-none-any.whl","/fixtures/de440s.bsp"],check=True)
    raise SystemExit(0)
suite=unittest.TestSuite(unittest.defaultTestLoader.discover("tests",pattern=pattern)
                         for pattern in ("test_daily_feedback.py","test_intent_model.py","test_daily_live_release.py","test_daily_review.py"))
result=unittest.TextTestRunner(verbosity=1).run(suite)
if not result.wasSuccessful() or result.skipped: raise SystemExit(1)
dir=Path("/fixtures")
kernel,wheel=dir/"de440s.bsp",dir/"certifi-2025.10.5-py3-none-any.whl"
day=lookup("6th December 2023 Delhi",False,kernel,wheel,structured=True)
assert "Margashirsha (Purnimanta)" in day["text"] and "Kartika (Amanta)" in day["text"]
assert day["context"]["basis"]["purnimanta"]["tithi"]==9
instant=lookup("7 December 2023 at 4 AM Delhi",False,kernel,wheel,structured=True)
assert instant["context"]["basis"]["amanta"]["birth_basis"]=="instant"
rule=instant["context"]["basis"]["amanta"] | {"repeated":"review"}
assert anniversary(rule,2027,kernel,wheel)["day"]=="2027-11-23"
assert anniversary(rule,2028,kernel,wheel) is None
print("PASS isolated actual sunrise/instant naming and evidence-bounded annual computation")
# Historical tests must use the same astronomy-only certifi overlay as live lookup.
subprocess.run([sys.executable,"-I","-S","-B","-c",r"""
import sys, sysconfig, unittest
sys.path[:0]=[sys.argv[1],"/repo"]
sys.path.extend([sysconfig.get_path("purelib"),sysconfig.get_path("platlib")])
tests=unittest.defaultTestLoader.discover("/repo/tests",pattern="test_historical_panchang.py")
result=unittest.TextTestRunner(verbosity=1).run(tests)
if not result.wasSuccessful() or result.skipped: raise SystemExit(1)
""",str(wheel)],check=True)

PY
stage=postgres_start
POSTGRES_PASSWORD=$(openssl rand -hex 32) docker run --network none --pull never -d \
  --label "org.dincharya.feedback-fixture=$mark" --tmpfs /var/lib/postgresql/data \
  -e POSTGRES_PASSWORD -e POSTGRES_DB=dincharya_personal_candidate "$pg" > "$tmp/id"
id=$(<"$tmp/id")
sql() {
  docker exec -i "$id" psql -XqAt -v ON_ERROR_STOP=1 -v VERBOSITY=verbose -U postgres \
    -d dincharya_personal_candidate "$@"
}
ready=false
for _ in {1..45}; do
  if [[ $(docker exec "$id" cat /proc/1/comm 2>/dev/null) == postgres ]] && sql -c 'SELECT 1' >/dev/null 2>&1; then ready=true; break; fi
  sleep 1
done
[[ $ready == true ]]
steps=(database/personal/000[1-6]_*.sql)
if [[ "$mode" == completion ]]; then
  steps+=(database/personal/0007_delhi_lunar_coverage.sql tests/daily_completion.sql)
else
  steps+=(tests/daily_feedback.sql)
fi
for item in "${steps[@]}"; do
  stage=${item##*/}
  if sql -f - < "$item" > "$tmp/result" 2> "$tmp/error"; then
    printf 'PASS %s\n' "$stage"
  else
    rc=$?
    sed -nE 's/^psql:[^:]*:([0-9]+): ERROR:[[:space:]]+([0-9A-Z]{5}):.*/input_line=\1 SQLSTATE=\2/p' "$tmp/error" >&2
    sed -nE 's/^CONTEXT:.*(PL\/pgSQL function (beta\.)?[A-Za-z_]+|SQL function (beta\.)?[A-Za-z_]+).*/context=\1/p' "$tmp/error" >&2
    exit "$rc"
  fi
done
if [[ "$mode" == completion ]]; then
  echo 'PASS additive Delhi evidence register and runtime write fences'
  exit 0
fi
stage=cancelled_replay
sql -c "SET SESSION AUTHORIZATION personal_worker; SELECT beta.acquire(); SELECT beta.roll_forward();" >/dev/null
[[ $(sql -c "SELECT count(*) FROM beta.occurrence o JOIN beta.proposal p ON p.id=o.rule WHERE p.request_id=201 AND o.enabled") == 0 ]]
echo 'PASS scoped annual projection, no duplicates, confirmed cancellation and past projection fencing'
stage=compatibility_rollback
before_counts=$(sql -c "SELECT (SELECT count(*) FROM beta.proposal),(SELECT count(*) FROM beta.occurrence),(SELECT count(*) FROM beta.slot),(SELECT count(*) FROM beta.ui_call),(SELECT count(*) FROM beta.lunar_schedule),(SELECT count(*) FROM beta.llm_spend)")
sql -f - < scripts/daily-feedback-compat.sql > "$tmp/compat" 2> "$tmp/compat-error"
[[ $(sql -c "SELECT (SELECT count(*) FROM beta.proposal),(SELECT count(*) FROM beta.occurrence),(SELECT count(*) FROM beta.slot),(SELECT count(*) FROM beta.ui_call),(SELECT count(*) FROM beta.lunar_schedule),(SELECT count(*) FROM beta.llm_spend)") == "$before_counts" ]]
[[ $(sql -c "SET SESSION AUTHORIZATION personal_gateway; SELECT beta.acquire(); SELECT count(*) FROM beta.ui_rules(901,902);" | tail -1) == 25 ]]
echo 'PASS compatibility rollback leaves ledgers intact and restores the legacy page cap'
