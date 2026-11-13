"""Focused prototype tests only; use the separate pinned environment and public kernel."""
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from prototypes.panchang.astronomy import Astronomy, DELHI, METADATA, Unsupported, UTC


class AstronomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        kernel=os.environ.get('DINCHARYA_PUBLIC_DE440S')
        if not kernel:
            raise RuntimeError('Explicit public DE440s path is required; no automatic download')
        cls.kernel=kernel
        cls.a=Astronomy(kernel)

    @classmethod
    def tearDownClass(cls):
        cls.a.close()

    def test_nasa_phase_references(self):
        refs=json.loads(Path('prototypes/panchang/references.json').read_text())
        for row in refs['transitions']:
            if row['source']!='nasa_phases': continue
            at=datetime.fromisoformat(row['at'])
            actual=self.a.transitions(at-timedelta(hours=1),at+timedelta(hours=1))
            self.assertEqual(len(actual),1)
            self.assertEqual(actual[0]['ordinal'],row['ordinal'])
            self.assertLessEqual(abs((datetime.fromisoformat(actual[0]['at'])-at).total_seconds()),60)

    def test_all_thirty_intervals_monotonic_wrap_and_transition_sides(self):
        start=datetime(2023,7,17,tzinfo=UTC); end=start+timedelta(days=32)
        rows=self.a.transitions(start,end)
        self.assertGreaterEqual(len(rows),30)
        self.assertEqual({r['ordinal'] for r in rows},set(range(1,31)))
        for first,last in zip(rows,rows[1:]):
            self.assertLess(first['at'],last['at'])
            self.assertEqual(last['ordinal'],first['ordinal']%30+1)
        for row in rows:
            at=datetime.fromisoformat(row['at'])
            self.assertLessEqual(row['bracket_seconds'],0.05)
            self.assertEqual(self.a.tithi_at(at-timedelta(seconds=1)),(row['ordinal']-2)%30+1)
            self.assertEqual(self.a.tithi_at(at+timedelta(seconds=1)),row['ordinal'])
        self.assertEqual(rows,self.a.transitions(start,end))

    def test_instant_and_sunrise_are_distinct_and_timezone_equivalent(self):
        dawn=self.a.at_sunrise(date(2026,1,13))
        evening=datetime(2026,1,13,18,tzinfo=DELHI)
        self.assertEqual(dawn['ordinal'],25)
        self.assertEqual(self.a.tithi_at(evening),26)
        self.assertEqual(self.a.tithi_at(evening),self.a.tithi_at(evening.astimezone(UTC)))
        self.assertEqual(self.a.tithi_at(evening),self.a.tithi_interval(evening)['ordinal'])

    def test_sunrise_hypotheses_are_distinct_not_claimed_equivalent(self):
        day=date(2026,1,14)
        first=self.a.sunrise(day)
        later=self.a.sunrise(day,'pac_47_hypothesis')
        self.assertLess(first,later)
        self.assertLess((later-first).total_seconds(),60)
        self.assertEqual(first.astimezone(DELHI).date(),day)
        with self.assertRaises(Unsupported): self.a.sunrise(day,'unreviewed')

    def test_boundary_uncertainty_requires_review(self):
        row=self.a.transitions(datetime(2023,7,17,tzinfo=UTC),datetime(2023,7,18,tzinfo=UTC))[0]
        at=datetime.fromisoformat(row['at'])
        for delta in (-1,1):
            self.assertTrue(self.a.tithi_interval(at+timedelta(seconds=delta))['review_required'])
        with patch.object(self.a,'sunrise',return_value=at+timedelta(seconds=1)):
            self.assertTrue(self.a.at_sunrise(date(2023,7,17))['review_required'])

    def test_repeated_and_skipped_dates_are_not_duplicate_or_guessed(self):
        repeated=self.a.monthly_preview(9,date(2026,11,1),date(2026,12,1))
        self.assertEqual(len(repeated),1)
        self.assertEqual(repeated[0]['sunrise_dates'],['2026-11-18','2026-11-19'])
        self.assertEqual(repeated[0]['selected_date'],'2026-11-18')
        skipped=self.a.monthly_preview(11,date(2026,11,1),date(2026,12,1))
        self.assertEqual(len(skipped),1)
        self.assertEqual(skipped[0]['sunrise_dates'],[])
        self.assertIsNone(skipped[0]['selected_date'])
        self.assertEqual(skipped[0]['status'],'needs_review')

    def test_month_boundaries_and_intercalary_hypothesis_are_not_month_labels(self):
        instant=datetime(2023,7,25,tzinfo=UTC)
        amanta=self.a.month_boundaries(instant,'amanta')
        purnimanta=self.a.month_boundaries(instant)
        self.assertTrue(amanta['start'].startswith('2023-07-17'))
        self.assertTrue(amanta['end'].startswith('2023-08-16'))
        self.assertTrue(purnimanta['start'].startswith('2023-07-03'))
        self.assertTrue(purnimanta['end'].startswith('2023-08-01'))
        for convention in ('amanta','purnimanta'):
            with self.assertRaises(Unsupported): self.a.month_label(instant,convention)
        with self.assertRaises(Unsupported): self.a.annual_preview(month='shravana',ordinal=9)
        self.assertEqual(set(self.a.lunation_diagnostics(instant)['constant_offset_ingress_counts'].values()),{0})
        ordinary=self.a.lunation_diagnostics(datetime(2023,8,25,tzinfo=UTC))
        self.assertEqual(set(ordinary['constant_offset_ingress_counts'].values()),{1})

    def test_invalid_dates_ranges_inputs_fail_closed(self):
        for value in (datetime(2023,1,1),datetime(1899,1,1,tzinfo=UTC),datetime(2101,1,1,tzinfo=UTC),'2023-01-01'):
            with self.subTest(value=value),self.assertRaises(Unsupported): self.a.tithi_at(value)
        start=datetime(2023,1,1,tzinfo=UTC)
        for end in (start,start-timedelta(days=1),start+timedelta(days=371)):
            with self.assertRaises(Unsupported): self.a.transitions(start,end)
        for ordinal in (True,0,31,'11'):
            with self.assertRaises(Unsupported): self.a.monthly_preview(ordinal,date(2023,1,1),date(2023,2,1))
        with self.assertRaises(Unsupported): self.a.month_boundaries(start,'unknown')

    def test_supported_instant_endpoints(self):
        for value in (datetime(1900,1,1,tzinfo=UTC),datetime(2100,12,31,23,59,tzinfo=UTC)):
            self.assertIn(self.a.tithi_at(value),range(1,31))
            # Raw instants are supported; complete straddling intervals are not.
            with self.assertRaises(Unsupported): self.a.tithi_interval(value)

    def test_missing_symlink_wrong_size_digest_and_dependency_reject(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'not-an-ephemeris.bsp'
            with self.assertRaises(Unsupported): Astronomy(path)
            path.write_bytes(b'Invented invalid public data')
            with self.assertRaises(Unsupported): Astronomy(path)
            link=Path(d)/'link.bsp'; link.symlink_to(self.kernel)
            with self.assertRaises(Unsupported): Astronomy(link)
            meta=json.loads(METADATA.read_text()); meta['sha256']='0'*64
            source=Path(d)/'synthetic-metadata.json'; source.write_text(json.dumps(meta))
            with patch('prototypes.panchang.astronomy.METADATA',source),self.assertRaises(Unsupported):
                Astronomy(self.kernel)
        with patch('prototypes.panchang.astronomy.importlib.metadata.version',return_value='wrong'):
            with self.assertRaises(Unsupported): Astronomy(self.kernel)

    def test_runtime_does_not_need_network(self):
        with (patch.object(socket,'create_connection',side_effect=AssertionError('Network forbidden')),
              patch.object(socket.socket,'connect',side_effect=AssertionError('Network forbidden'))):
            with Astronomy(self.kernel) as a:
                self.assertEqual(a.tithi_at(datetime(2026,1,14,8,tzinfo=UTC)),26)
                self.assertEqual(a.at_sunrise(date(2026,1,14))['ordinal'],26)
