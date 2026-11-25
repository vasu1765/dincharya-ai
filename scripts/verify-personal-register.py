"""Verify the owner's reviewed source bytes and decisions before candidate acceptance."""
import hashlib
import json
from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[1]
validate = runpy.run_path(str(root / 'scripts/review-source-adoption.py'))['validate_decisions']
for register, record in [('m2b-repository-review','m2b-owner-decisions'),
                         ('m2-exit-sources','m2-exit-owner-decisions')]:
    source = (root / 'docs' / (register+'.json')).read_bytes()
    package = json.loads(source)
    validate(package, source, json.loads((root / 'docs' / (record+'.json')).read_bytes()))
    for artifact in package['artifacts']:
        path = root / artifact['path']
        if path.resolve() != path or hashlib.sha256(path.read_bytes()).hexdigest() != artifact['sha256']:
            raise SystemExit('Reviewed bytes differ: '+artifact['path'])
    print(f"{register}: {len(package['artifacts'])} matched")
