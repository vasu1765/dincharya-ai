#!/usr/bin/env bash
# All veths and routes exist only inside ephemeral Linux namespaces.
set -euo pipefail
stage() {
  current_stage=$1
  printf 'STAGE %s\n' "$current_stage" >&2
}
stage preflight
trap 'rc=$?; if ((rc)); then printf "FAIL stage=%s exit=%d\n" "$current_stage" "$rc" >&2; fi' EXIT
: "${REV:?set exact revision}"
[[ $(git rev-parse HEAD) == "$REV" && -z $(git status --porcelain) ]]
sha256sum -c docs/attended-connect.sha256
if [[ ${1:-} != --isolated ]]; then
  stage outer_namespace
  exec unshare --net -- bash "$0" --isolated
fi
stage namespace_isolation
# Require a fresh outer namespace without physical interfaces or a default route.
[[ $(ip -o link show | wc -l) -eq 1 ]]
export PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1
tmp=$(mktemp -d)
children=()
cleanup() {
  local rc=$? failed=0 pid
  trap - EXIT
  if ((rc)); then printf 'FAIL stage=%s exit=%d\n' "$current_stage" "$rc" >&2; fi
  stage cleanup
  for pid in "${children[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait || failed=1
  rm -rf -- "$tmp" || failed=1
  if ((failed)); then
    printf 'FAIL namespace cleanup\n' >&2
  else
    printf 'PASS namespace children reaped and scratch removed\n'
  fi
  if ((rc)); then exit "$rc"; fi
  exit "$failed"
}
trap cleanup EXIT
trap 'exit 130' INT TERM
for role in app gateway origin; do
  stage "namespace_${role}"
  unshare -n -- sleep 180 &
  p=$!
  children+=("$p")
  for _ in {1..30}; do
    [[ $(readlink "/proc/$p/ns/net") != "$(readlink /proc/self/ns/net)" ]] && break
    sleep .1
  done
  [[ -d /proc/$p && $(readlink "/proc/$p/ns/net") != "$(readlink /proc/self/ns/net)" ]]
  printf -v "$role" '%d' "$p"
  nsenter -t "$p" -n ip link set dev lo up
done
link() {
  stage "veth_${1}_create"
  ip link add "$1" type veth peer name "$4"
  stage "veth_${1}_move"
  ip link set dev "$1" netns "$2"
  stage "veth_${1}_peer_move"
  ip link set dev "$4" netns "$5"
  stage "veth_${1}_configure"
  nsenter -t "$2" -n ip addr add "$3" dev "$1"
  nsenter -t "$5" -n ip addr add "$6" dev "$4"
  nsenter -t "$2" -n ip link set dev "$1" up
  nsenter -t "$5" -n ip link set dev "$4" up
}
link op "$app" 172.29.241.2/29 gw "$gateway" 172.29.241.3/29
link uplink0 "$gateway" 198.18.0.1/30 peer "$origin" 198.18.0.2/30
stage fixture_routes
pin=93.184.216.34
nsenter -t "$origin" -n ip addr add "$pin/32" dev lo
nsenter -t "$gateway" -n ip route add "$pin/32" via 198.18.0.2
stage alternate_port_positive_control
# Prove an alternate endpoint works before the restrictive rules are loaded.
nsenter -t "$origin" -n python3 -m http.server 444 --bind 0.0.0.0 > /dev/null 2>&1 &
children+=("$!")
for _ in {1..40}; do
  nsenter -t "$origin" -n ss -lnt | grep -q ':444 ' && break
  sleep .1
done
nsenter -t "$gateway" -n python3 -c 'import socket; socket.create_connection(("93.184.216.34",444),2).close()'
for role in app gateway; do
  stage "policy_${role}_load"
  python3 -m scripts.attended_net_policy "$role" "$pin" | nsenter -t "${!role}" -n nft -f -
  stage "policy_${role}_readback"
  python3 -c 'from scripts.attended_net_policy import verify;import sys;verify(*sys.argv[1:])' "${!role}" "$role" "$pin"
done
stage tls_fixture_start
openssl req -new -x509 -nodes -newkey rsa:2048 -days 1 -subj /CN=api.telegram.org -addext subjectAltName=DNS:api.telegram.org -keyout "$tmp/k" -out "$tmp/c" 2>/dev/null
nsenter -t "$origin" -n openssl s_server -accept "$pin:443" -key "$tmp/k" -cert "$tmp/c" -www -quiet > /dev/null 2>&1 &
children+=("$!")
nsenter -t "$gateway" -n python3 -m dincharya.attended_connect "$pin" &
children+=("$!")
for _ in {1..40}; do
  nsenter -t "$gateway" -n ss -lnt | grep -q ':8443 ' && break
  sleep .1
done
stage connect_tls_and_destination_denials
nsenter -t "$app" -n python3 - "$tmp/c" <<'PYTHON'
import socket,ssl,sys
from dincharya.attended_connect import LISTENER,PORT
def header(sock):
    data=b''
    while not data.endswith(b'\r\n\r\n') and len(data)<2048:
        byte=sock.recv(1)
        if not byte:break
        data+=byte
    return data
for target in ("denied.invalid:443","api.telegram.org:80","93.184.216.34:443","api.telegram.org:443"):
    with socket.create_connection((LISTENER,PORT),timeout=2) as sock:
        sock.sendall(f"CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n\r\n".encode())
        reply=header(sock)
        if target=="api.telegram.org:443":
            assert reply.startswith(b"HTTP/1.1 200 ")
            with ssl.create_default_context(cafile=sys.argv[1]).wrap_socket(sock,server_hostname="api.telegram.org") as tls:
                tls.sendall(b"GET / HTTP/1.0\r\n\r\n")
                assert b"200" in tls.recv(64)
        else:
            assert reply.startswith(b"HTTP/1.1 403 ")
PYTHON
for role in gateway app; do
  stage "direct_${role}_denials"
  nsenter -t "${!role}" -n python3 - "$role" <<'PYTHON'
import socket,sys
# Even a directly attached, listening alternate origin must be unreachable.
for host,port in ([("198.18.0.2",444),("93.184.216.34",444)] if sys.argv[1]=="gateway"
                  else [("172.29.241.3",444),("93.184.216.34",443)]):
    try:
        conn=socket.create_connection((host,port),timeout=.4)
    except OSError: continue
    conn.close()
    raise AssertionError("Unexpected direct connection")
PYTHON
done
echo 'PASS synthetic CONNECT, TLS, namespace policies and denied destinations'
