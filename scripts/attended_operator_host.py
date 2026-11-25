"""Attended host preflight for an already staged, stopped operator. Checks the parked operator and gateway before manual exec."""
import argparse
import json
from pathlib import Path
import subprocess

from dincharya.attended_operator import Approval
from dincharya.attended_runtime import verify_images, WHEEL, WHEEL_SHA, KERNEL_SHA
import hashlib
from scripts.attended_net_policy import verify as verify_rules, APP, DB, RELAY, LISTENER, OPERATOR


def output(*argv):
    return subprocess.check_output(argv,text=True).strip()


def topology(pg,app,relay,gateway):
    def networks(c):
        return c["NetworkSettings"]["Networks"]
    service, = networks(pg)
    link, = set(networks(app))-{service}
    uplink, = set(networks(gateway))-{link}
    plans=[(service, True, [(app,APP),(pg,DB),(relay,RELAY)]),
           (link, True, [(app,OPERATOR),(gateway,LISTENER)]),
           (uplink, False, [(gateway,None)])]
    for name,internal,peers in plans:
        network,=json.loads(output("docker","network","inspect",name))
        if (network["Driver"]!="bridge" or network["Internal"]!=internal or network["EnableIPv6"]
                or set(network["Containers"])!={c["Id"] for c,_ in peers}):
            raise ValueError("Unexpected bridge or peer")
        for c,ip in peers:
            if ip and networks(c)[name]["IPAddress"]!=ip:
                raise ValueError("Unexpected peer address")
    for c,names in [(pg,{service}),(relay,{service}),(app,{service,link}),(gateway,{link,uplink})]:
        if set(networks(c))!=names:
            raise ValueError("Unexpected network attachment")


def verify(manifest,pin,containers):
    revision=output("git","rev-parse","HEAD")
    if output("git","status","--porcelain"):
        raise ValueError("Clean exact checkout required")
    daemon=output("docker","info","--format","{{.ID}}")
    raw=manifest.read_bytes()
    a=Approval.load(raw,pin,revision,daemon)
    verify_images(a.pg,a.app,a.n8n)
    if daemon != "44c1ef83-c50e-4ecc-8f19-4b112bc40f29" or a.kernel_sha256 != KERNEL_SHA:
        raise ValueError("Unexpected daemon or ephemeris")
    if manifest.name != "manifest.json" or manifest.is_symlink():
        raise ValueError("Expected exact regular manifest mount")
    if hashlib.sha256((manifest.parent/WHEEL).read_bytes()).hexdigest() != WHEEL_SHA:
        raise ValueError("Unreviewed astronomy overlay")
    if len(set(containers))!=4:
        raise ValueError("Four distinct containers required")
    pg,app,relay,gateway=json.loads(output("docker","inspect",*containers))
    if len({c["Id"] for c in (pg,app,relay,gateway)})!=4:
        raise ValueError("Duplicate container identity")
    topology(pg,app,relay,gateway)
    namespaces=set()

    for c,role in [(pg,"db"),(relay,"relay"),(app,"app"),(gateway,"gateway")]:
        if not c["State"]["Running"] or c["State"]["Pid"]<=1:
            raise ValueError("Fresh running namespace required")
        pid=c["State"]["Pid"]
        proc=Path("/proc")/str(pid)
        if c["Id"] not in (proc/"cgroup").read_text():
            raise ValueError("Container PID cannot be tied to this daemon host")
        inode=(proc/"ns/net").stat().st_ino
        if inode in namespaces:
            raise ValueError("Shared container network namespace")
        namespaces.add(inode)
        verify_rules(pid,role,a.telegram_ipv4)
    for c in (app,gateway):
        h=c["HostConfig"]
        if (set(h["CapDrop"] or [])!={"ALL"} or h["CapAdd"] or not h["ReadonlyRootfs"]
                or not c["Config"]["User"].split(":")[0].isdecimal()
                or int(c["Config"]["User"].split(":")[0])==0
                or c["Config"]["Entrypoint"]!=["sleep"] or c["Config"]["Cmd"]!=["infinity"]
                or not any(v in ("no-new-privileges","no-new-privileges:true") for v in h["SecurityOpt"] or [])):
            raise ValueError("Expected parked unprivileged runtime")
    if set(app["HostConfig"]["ExtraHosts"] or [])!={f"db:{DB}",f"relay:{RELAY}"} or set(relay["HostConfig"]["ExtraHosts"] or [])!={f"app:{APP}"}:
        raise ValueError("Static service mapping required")
    if not app["HostConfig"]["ReadonlyRootfs"]:
        raise ValueError("Read-only operator filesystem required")
    image, = json.loads(output("docker","image","inspect",a.app))
    baseline = dict(item.split("=",1) for item in image["Config"]["Env"])
    actual_env = app["Config"]["Env"]
    expected_env = {**baseline,"PYTHONPATH":"/candidate"}
    if sorted(actual_env) != sorted(k+"="+v for k,v in expected_env.items()):
        raise ValueError("Unexpected operator environment override")
    for c,img in zip((pg,app,relay,gateway),(a.pg,a.app,a.n8n,a.app)):
        if (c["Image"]!=img or c["HostConfig"]["Privileged"]
                or c["HostConfig"]["RestartPolicy"]["Name"] not in ("","no")
                or c["HostConfig"]["NetworkMode"]=="host" or c["HostConfig"]["PortBindings"]):
            raise ValueError("Unexpected container configuration")
    if (not pg["State"]["Running"] or not relay["State"]["Running"] or not app["State"]["Running"]
            or "/var/lib/postgresql/data" not in (pg["HostConfig"].get("Tmpfs") or {})
            or app["Config"]["Hostname"]!=daemon):
        raise ValueError("Disposable attended topology required")
    mounts={m["Destination"]:m for m in app["Mounts"]}
    if set(mounts)!={"/candidate","/run/attended"} or any(m["RW"] for m in mounts.values()):
        raise ValueError("Only read-only candidate and approval mounts permitted")
    if Path(mounts["/run/attended"]["Source"]).resolve()!=manifest.resolve().parent:
        raise ValueError("Different approval mount")
    tree=Path(mounts["/candidate"]["Source"])
    gm=gateway["Mounts"]
    if (len(gm)!=1 or gm[0]["Destination"]!="/candidate" or gm[0]["RW"]
            or gm[0]["Source"]!=str(tree) or gateway["Config"]["WorkingDir"]!="/candidate"
            or sorted(gateway["Config"]["Env"])!=sorted(actual_env)):
        raise ValueError("Gateway source or configuration mismatch")
    # Only files in the reviewed commit may be imported; reject injected bytecode,
    # symlinked directories and alternate source files.
    expected={}
    for line in output("git","ls-tree","-r",revision,"--","dincharya","prototypes/panchang").splitlines():
        meta,name=line.split("\t",1)
        mode,kind,oid=meta.split()
        if kind!="blob" or mode not in ("100644","100755"):
            raise ValueError("Unexpected source type")
        expected[name]=oid
    actual={}
    for path in tree.rglob("*"):
        if path.is_symlink():
            raise ValueError("Unexpected source link")
        if path.is_file():
            data=path.read_bytes()
            actual[str(path.relative_to(tree))]=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
    if not expected or actual!=expected:
        raise ValueError("Source archive differs from approved revision")
    if app["Config"]["WorkingDir"]!="/candidate" or "PYTHONPATH=/candidate" not in app["Config"]["Env"]:
        raise ValueError("Unexpected module path")
    return a

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest",type=Path)
    parser.add_argument("digest")
    parser.add_argument("containers",nargs=4,metavar="CONTAINER")
    args=parser.parse_args()
    verify(args.manifest,args.digest,args.containers)
    print("PASS host, revision, image IDs and disposable PG preflight")
