"""Render and compare namespace-local nft rules for one fresh attended topology."""
import argparse
import os
import subprocess

from dincharya.attended_connect import upstream, LISTENER, OPERATOR, PORT

APP = "172.29.240.2"
DB = "172.29.240.3"
RELAY = "172.29.240.4"
TABLE = "dincharya_attended"


def rules(role, pin):
    target = upstream(pin)
    flows = {
        "gateway":[(target,443)],
        "app":[(DB,5432),(RELAY,5678),(LISTENER,PORT)],
        "relay":[(APP,8080),("127.0.0.1",5678)],
        "db":[("127.0.0.1",5432)],
    }[role]
    # Scope reply traffic to accepted inbound TCP clients as well. No UDP or
    # Docker DNS. Output hook precedes Docker's OUTPUT destination NAT.
    clients = {
        "gateway":[(OPERATOR,PORT)], "db":[(APP,5432),("127.0.0.1",5432)],
        "app":[(RELAY,8080)], "relay":[(APP,5678),("127.0.0.1",5678)],
    }[role]
    lines=["table inet "+TABLE+" {","chain output {",
           "type filter hook output priority -150; policy drop;"]
    lines += [f"ip daddr {addr} tcp dport {port} accept" for addr,port in flows]
    lines += [f"ip daddr {addr} tcp sport {port} ct direction reply accept" for addr,port in clients]
    return "\n".join(lines+["}","}"])+"\n"


def verify(pid,role,pin):
    if int(pid)<=1 or os.stat(f"/proc/{int(pid)}/ns/net").st_ino == os.stat("/proc/self/ns/net").st_ino:
        raise ValueError("Distinct container network namespace required")
    cmd=["nsenter","-t",str(pid),"-n","nft","-nn","-s","-y","list","table","inet",TABLE]
    actual=subprocess.check_output(cmd,text=True)
    def tokens(s):
        return s.split()
    if tokens(actual)!=tokens(rules(role,pin)):
        raise ValueError("Namespace egress policy mismatch")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("role",choices=["app","db","relay","gateway"])
    p.add_argument("pin")
    args=p.parse_args()
    print(rules(args.role,args.pin),end="")
