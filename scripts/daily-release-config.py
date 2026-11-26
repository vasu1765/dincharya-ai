"""Render reviewed provisioning SQL and the inactive native workflow. No side effects."""
import argparse
import hashlib
import json
from pathlib import Path

from dincharya.daily_live import Approval


def provision(raw, revision, host):
    # Preparation may precede the approved window.
    start=json.loads(raw)["start"]
    a=Approval.read(raw,revision,host,lambda:start)
    pin=hashlib.sha256(raw).hexdigest()
    # Only validated integers, a two-value enum and an internally computed digest enter SQL.
    return f"""BEGIN;
DO $$ BEGIN
 IF current_database()<>'dincharya_personal_candidate' OR current_setting('server_version_num')::int/10000<>17
 THEN RAISE EXCEPTION 'personal PG17 required'; END IF;
END $$;
INSERT INTO beta.live_release(epoch,digest,profile,opens,closes)
 SELECT epoch,'{pin}','{a.profile}',to_timestamp({a.start}),to_timestamp({a.end})
 FROM beta.authority WHERE singleton AND enabled AND recipient={a.owner} AND bot={a.bot};
DO $$ BEGIN
 IF NOT EXISTS(SELECT FROM beta.live_release WHERE digest='{pin}') THEN RAISE EXCEPTION 'authority absent'; END IF;
END $$;
COMMIT;"""


def workflow():
    path=Path(__file__).resolve().parents[1]/"workflows/m2g-lunar-acceptance.json"
    value=json.loads(path.read_bytes())
    hook,relay=value["nodes"]
    if value["active"] is not False or relay["parameters"]["url"]!="http://dincharya-lunar/lunar":
        raise ValueError("Unexpected relay source")
    relay["parameters"]["url"]="http://dincharya-lunar:8080/lunar"
    value["name"]="Personal signed daily gateway"
    return value


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("workflow","release"))
    parser.add_argument("--manifest",type=Path)
    parser.add_argument("--revision")
    parser.add_argument("--host")
    args=parser.parse_args()
    print(json.dumps(workflow()) if args.action=="workflow" else provision(
        args.manifest.read_bytes(),args.revision,args.host))
