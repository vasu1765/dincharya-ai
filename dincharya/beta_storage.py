"""Render the isolated storage slice for operator review. Never invoke Docker."""
import argparse
import json
from pathlib import Path

from dincharya.beta_preflight import validate_plan


def storage_project(plan):
    validate_plan(plan)
    digest = plan["services"]["postgres"]["image"]
    if digest == "pending":
        raise ValueError("Review and record the PostgreSQL 17 image digest first")
    return {
        "name": "dincharya-personal-beta",
        "services": {"postgres": {
            "profiles": ["storage-review"], "image": "postgres@" + digest,
            "pull_policy": "never", "restart": "no", "network_mode": "none",
            "environment": {"POSTGRES_DB": plan["database"]["name"],
                            "POSTGRES_USER": "beta_bootstrap",
                            "POSTGRES_PASSWORD_FILE": "/run/secrets/bootstrap"},
            "secrets": ["bootstrap"], "volumes": ["pgdata:/var/lib/postgresql/data"],
            "command": ["postgres", "-c", "listen_addresses="],
            "healthcheck": {"test": ["CMD-SHELL", "test \"$$(cat /proc/1/comm)\" = postgres && psql -XAtq -U beta_bootstrap -d dincharya_personal_beta -c 'SHOW server_version_num' | grep -Ex '17[0-9]{4}'"],
                            "interval": "10s", "timeout": "4s", "retries": 6},
            "stop_grace_period": "1m",
        }},
        "volumes": {"pgdata": {}},
        "secrets": {"bootstrap": {"file": "${BETA_BOOTSTRAP_FILE:?owner-only external file required}"}},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    from dincharya.beta_preflight import verify_file
    verify_file(args.plan)
    print(json.dumps(storage_project(json.loads(args.plan.read_bytes())), indent=2))
