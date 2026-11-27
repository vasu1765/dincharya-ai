"""Render a first-provisioning transaction directly into an approved psql pipe."""
import argparse
import os
from pathlib import Path
import re
import stat
import sys

ROLES=("personal_gateway","personal_worker","personal_observer","personal_backup")


def transaction(keys):
    if set(keys)!=set(ROLES) or len(set(keys.values()))!=len(ROLES):
        raise ValueError("Four distinct scoped role keys required")
    if any(not re.fullmatch(r"[0-9a-f]{64}",v) for v in keys.values()):
        raise ValueError("Use independently generated 32-byte hex keys")
    statements=["BEGIN;", """DO $$ BEGIN
 IF current_database()<>'dincharya_personal_candidate' OR current_setting('server_version_num')::int/10000<>17
 OR EXISTS(SELECT FROM beta.authority) OR EXISTS(SELECT FROM beta.live_release)
 OR (SELECT count(*) FROM pg_roles WHERE rolname IN
 ('personal_gateway','personal_worker','personal_observer','personal_backup')
 AND NOT rolcanlogin AND NOT rolsuper AND NOT rolcreaterole AND NOT rolcreatedb AND NOT rolbypassrls)<>4
 THEN RAISE EXCEPTION 'fresh scoped personal roles required'; END IF;
END $$;"""]
    for role in ROLES:
        statements.append(f"ALTER ROLE {role} LOGIN PASSWORD '{keys[role]}';")
    return "\n".join(statements+["COMMIT;"])


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-key-directory",type=Path,required=True)
    root=parser.parse_args().private_key_directory
    if not root.is_absolute() or root.is_symlink() or not stat.S_ISFIFO(os.fstat(1).st_mode):
        raise SystemExit("Private directory and direct pipe required")
    keys={}
    for role in ROLES:
        with os.fdopen(os.open(root/(role+".key"),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)) as handle:
            meta=os.fstat(handle.fileno())
            if not stat.S_ISREG(meta.st_mode) or meta.st_uid!=os.geteuid() or meta.st_mode & 0o077 or meta.st_size>66:
                raise SystemExit("Unsafe role key")
            keys[role]=handle.read().strip()
    sys.stdout.write(transaction(keys))
