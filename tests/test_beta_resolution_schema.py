"""Guard the resolution DDL and its exact-replay binding before the PG17 rehearsal."""
from pathlib import Path
import unittest


class ResolutionSchemaTests(unittest.TestCase):
    def test_resolution_uses_nonreserved_permit_identifier(self):
        path = Path(__file__).resolve().parents[1] / "database/personal_beta/0001_civil.sql"
        sql = path.read_text(encoding="utf-8").lower()
        columns = sql.split("create table beta.resolution (", 1)[1].split(");", 1)[0]
        self.assertNotRegex(columns, r"\bauthorization\s+uuid\b")
        self.assertRegex(columns, r"\bpermit_id\s+uuid\s+unique\s+not null\s+references\s+beta\.reconcile_permit\b")
        self.assertIn("r.permit_id", sql)
        self.assertNotRegex(sql, r"\br\.authorization\b")
