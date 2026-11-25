"""Owner-local, attended file handling. No networking. The token is provisioned separately."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

from dincharya.attended_operator import Approval
from dincharya.attended_runtime import verify_images, KERNEL_SHA


def private_directory(path):
    info=path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode & 0o077
            or path.absolute()!=path.resolve()):
        raise ValueError("Absolute private owner directory required")


def read(path):
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),"rb") as f:
        info=os.fstat(f.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode & 0o077 or info.st_size>65536):
            raise ValueError("Private regular owner file required")
        return f.read()


def write(path,data,*,replace=False):
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as tmp:
        name=Path(tmp.name)
        try:
            tmp.write(data)
            tmp.flush()
            os.fsync(tmp.fileno())
            if replace:
                os.replace(name,path)
            else:
                os.link(name,path)
        finally:
            name.unlink(missing_ok=True)


def receipt(state,raw):
    sha=read(state/"revision").decode().strip()
    if sha!=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip():
        raise ValueError("Checkout differs from staged revision")
    digest=hashlib.sha256(raw).hexdigest()
    a=Approval.load(raw,digest,sha,"44c1ef83-c50e-4ecc-8f19-4b112bc40f29")
    verify_images(a.pg,a.app,a.n8n)
    if a.profile!="laptop-beta" or a.kernel_sha256!=KERNEL_SHA or a.bot==93002 or a.owner==93001:
        raise ValueError("Personal attended manifest required")
    ids={k:read(state/k).decode().strip() for k in ("app","pg","relay")}
    import re
    if len(set(ids.values()))!=3 or not all(re.fullmatch("[a-f0-9]{64}",v) for v in ids.values()):
        raise ValueError("Invalid staged container IDs")
    return dict(version=1,manifest_sha256=digest,revision=sha,containers=ids)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("prepare","approve","start","stop"))
    p.add_argument("state",type=Path)
    p.add_argument("--input",type=Path)
    p.add_argument("--owner-approved-digest")
    args=p.parse_args(argv)
    state=args.state
    private_directory(state)
    session=state/"session"
    private_directory(session)
    file=session/"manifest.json"
    record=state/"owner-approval.json"
    if args.action=="stop":
        (session/"STOP").touch(exist_ok=True)
    else:
        if not (session/"STOP").is_file():
            raise ValueError("Fence the staged operator first")
        if args.action=="prepare":
            if args.input is None or record.exists():
                raise ValueError("Fresh unapproved stage and private input required")
            template=json.loads(read(file))
            if template.get("owner")!=93001 or template.get("bot")!=93002 or (session/"bot.key").exists():
                raise ValueError("Prepare requires an untouched synthetic stage")
            raw=read(args.input)
            supplied=json.loads(raw)
            fields={"bot","bot_username","owner","start","end","silent","reminder","question"}
            if set(supplied)==fields:
                raw=json.dumps({**template,**supplied},ensure_ascii=False,sort_keys=True,indent=2).encode()+b"\n"
            result=receipt(state,raw)
            write(file,raw,replace=True)
            print(result["manifest_sha256"])
            return
        result=receipt(state,read(file))
        digest=result["manifest_sha256"]
        if args.action=="approve":
            if args.owner_approved_digest!=digest:
                raise ValueError("Separate exact owner authorization required")
            # Exclusive creation. A record is never replaced or reissued in this stage.
            write(record,json.dumps(result,sort_keys=True).encode())
            return
        if json.loads(read(record))!=result:
            raise ValueError("Approval record differs from staged resources")
        os.environ.update(APPROVAL_DIGEST=digest,LIVE_SESSION_APPROVAL=digest)
    os.environ["REV"]=read(state/"revision").decode().strip()
    os.execvp("bash",["bash","scripts/laptop_beta.sh",args.action,str(state)])


if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit("Private session check failed ("+type(exc).__name__+")") from None
