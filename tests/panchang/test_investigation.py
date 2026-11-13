"""Selected public research fixtures do not enable calendar APIs."""
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from prototypes.panchang.astronomy import Astronomy, Unsupported
from prototypes.panchang.investigation import LahiriHypothesis


class InvestigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=Astronomy(os.environ['DINCHARYA_PUBLIC_DE440S'])
        cls.h=LahiriHypothesis(cls.a)
        cls.refs=json.loads(Path('prototypes/panchang/research-references.json').read_text())

    @classmethod
    def tearDownClass(cls): cls.a.close()

    def test_explicit_epoch_and_uncorrected_control(self):
        control=LahiriHypothesis(self.a,0)
        for r in self.refs['epoch_checks']:
            at=datetime.fromisoformat(r['at'])
            self.assertLess(abs((self.h.ayanamsa_at(at)-r['degrees'])*3600),.1)
            self.assertGreater(abs((control.ayanamsa_at(at)-r['degrees'])*3600),.5)

    def test_four_independent_solar_ingresses(self):
        for r in self.refs['solar_ingresses']:
            at=datetime.fromisoformat(r['at'])
            rows=self.h.solar_ingresses(at-timedelta(days=1),at+timedelta(days=1))
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['sign'],r['sign'])
            self.assertLessEqual(abs((datetime.fromisoformat(rows[0]['at'])-at).total_seconds()),60)

    def test_selected_amanta_cases_and_public_apis_stay_disabled(self):
        for r in self.refs['amanta_cases']:
            at=datetime.fromisoformat(r['at'])
            result=self.h.amanta_diagnostic(at)
            self.assertEqual(result['candidate_amanta_month'],r['month'])
            self.assertEqual(result['candidate_intercalation'],r['intercalation'])
            for convention in ('amanta','purnimanta'):
                with self.assertRaises(Unsupported): self.a.month_label(at,convention)
        with self.assertRaises(Unsupported): self.a.annual_preview(month='shravana',ordinal=1)

    def test_multiple_and_near_boundary_ingresses_fail_closed(self):
        at=datetime.fromisoformat('2023-07-25T06:00:00+00:00')
        bounds=self.a.month_boundaries(at,'amanta')
        start=datetime.fromisoformat(bounds['start'])
        middle=start+timedelta(days=10)
        two=[dict(at=middle.isoformat(),sign=1),dict(at=(middle+timedelta(days=1)).isoformat(),sign=2)]
        for rows in (two,[dict(at=(start-timedelta(seconds=1)).isoformat(),sign=1)]):
            with patch.object(self.h,'solar_ingresses',return_value=rows),self.assertRaises(Unsupported):
                self.h.amanta_diagnostic(at)

    def test_research_range_and_profile_fail_closed(self):
        for at in (datetime.fromisoformat('1899-12-31T00:00:00+00:00'),
                   datetime.fromisoformat('2101-01-01T00:00:00+00:00')):
            with self.assertRaises(Unsupported): self.h.ayanamsa_at(at)
            with self.assertRaises(Unsupported): self.h.solar_longitude(at)
            with self.assertRaises(Unsupported): self.h.amanta_diagnostic(at)
        with self.assertRaises(Unsupported): LahiriHypothesis(self.a,.5)
