"""Attended host preflight for an already staged, stopped operator. Starts nothing."""
import argparse
import json
from pathlib import Path
import subprocess

from dincharya.attended_operator import Approval
from dincharya.attended_runtime import verify_images, WHEEL, WHEEL_SHA, KERNEL_SHA
import hashlib


def output(*argv):
    return subprocess.check_output(argv,text=True).strip()


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
    if len(set(containers))!=3:
        raise ValueError("Distinct containers required")
    pg,app,relay=json.loads(output("docker","inspect",*containers))
    def networks(container):
        return set(container["NetworkSettings"]["Networks"])
    internal = networks(pg)
    egress = networks(app) - internal
    if len(internal)!=1 or networks(relay)!=internal or networks(app)!=internal|egress or len(egress)!=1 or not internal.issubset(networks(app)):
        raise ValueError("Unexpected attended network topology")
    private, outbound = json.loads(output("docker","network","inspect",*internal,*egress))
    if not private["Internal"] or outbound["Internal"]:
        raise ValueError("Incorrect network isolation")
    if set(private["Containers"] or {}) - {pg["Id"],app["Id"],relay["Id"]} or set(outbound["Containers"] or {}) - {app["Id"]}:
        raise ValueError("Unexpected network peer")
    if not app["HostConfig"]["ReadonlyRootfs"]:
        raise ValueError("Read-only operator filesystem required")
    image, = json.loads(output("docker","image","inspect",a.app))
    baseline = dict(item.split("=",1) for item in image["Config"]["Env"])
    actual_env = app["Config"]["Env"]
    expected_env = {**baseline,"PYTHONPATH":"/candidate"}
    if sorted(actual_env) != sorted(k+"="+v for k,v in expected_env.items()):
        raise ValueError("Unexpected operator environment override")
    for c,img in zip((pg,app,relay),(a.pg,a.app,a.n8n)):
        if (c["Image"]!=img or c["HostConfig"]["Privileged"]
                or c["HostConfig"]["RestartPolicy"]["Name"] not in ("","no")
                or c["HostConfig"]["NetworkMode"]=="host" or c["HostConfig"]["PortBindings"]):
            raise ValueError("Unexpected container configuration")
    if (not pg["State"]["Running"] or not relay["State"]["Running"] or app["State"]["Running"]
            or "/var/lib/postgresql/data" not in (pg["HostConfig"].get("Tmpfs") or {})
            or app["Config"]["Hostname"]!=daemon):
        raise ValueError("Disposable attended topology required")
    # The reviewed app image must contain the reviewed package, or use a read-only
    # git archive mounted at /candidate with PYTHONPATH and an explicit Python entrypoint.
    if app["Config"]["Entrypoint"] != ["python"] or app["Config"]["Cmd"] != [
            "-B","-m","dincharya.attended_operator","--attended","--approval",pin]:
        raise ValueError("Unexpected executable or approval pin")
    mounts={m["Destination"]:m for m in app["Mounts"]}
    if set(mounts)!={"/candidate","/run/attended"} or any(m["RW"] for m in mounts.values()):
        raise ValueError("Only read-only candidate and approval mounts permitted")
    if Path(mounts["/run/attended"]["Source"]).resolve()!=manifest.resolve().parent:
        raise ValueError("Different approval mount")
    tree=Path(mounts["/candidate"]["Source"])
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
    parser.add_argument("containers",nargs=3,metavar="CONTAINER")
    args=parser.parse_args()
    verify(args.manifest,args.digest,args.containers)
    print("PASS host, revision, image IDs and disposable PG preflight")
