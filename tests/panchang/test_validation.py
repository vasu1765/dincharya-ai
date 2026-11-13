"""Focused regressions for demonstrated numerical/range ambiguities."""
from datetime import date, datetime, timedelta
import os
import unittest
from unittest.mock import patch
import numpy as np

from prototypes.panchang.astronomy import Astronomy, MINIMUM, MAXIMUM, Unsupported, UTC


class BoundaryValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=Astronomy(os.environ['DINCHARYA_PUBLIC_DE440S'])

    @classmethod
    def tearDownClass(cls): cls.a.close()

    def test_floating_wrap_cannot_produce_tithi_31(self):
        with patch.object(self.a,'_longitudes',return_value=(0.0,-np.nextafter(0.0,1.0))):
            with self.assertRaises(Unsupported):
                self.a.tithi_at(datetime(2026,1,1,tzinfo=UTC))

    def test_exact_algebraic_boundaries_are_half_open(self):
        for phase in (0.0,12.0,180.0,348.0):
            with self.subTest(phase=phase),patch.object(self.a,'_longitudes',return_value=(0.0,phase)):
                self.assertEqual(self.a.tithi_at(datetime(2026,1,1,tzinfo=UTC)),int(phase/12)+1)
        for phase,expected in ((np.nextafter(12.0,0.0),1),(np.nextafter(12.0,360.0),2)):
            with patch.object(self.a,'_longitudes',return_value=(0.0,phase)):
                self.assertEqual(self.a.tithi_at(datetime(2026,1,1,tzinfo=UTC)),expected)

    def test_reported_boundary_and_millisecond_offsets_fail_closed(self):
        row=self.a.transitions(datetime(2023,7,17,tzinfo=UTC),datetime(2023,7,18,tzinfo=UTC))[0]
        t=datetime.fromisoformat(row['at'])
        for offset in (-.01,0,.001,.01):
            with self.subTest(offset=offset),self.assertRaisesRegex(Unsupported,'numerical transition uncertainty'):
                self.a.tithi_interval(t+timedelta(seconds=offset))
        for offset in (-.01,0,.01):
            near=t+timedelta(seconds=offset)
            for start,end in ((near,near+timedelta(hours=1)),(near-timedelta(hours=1),near)):
                with self.assertRaisesRegex(Unsupported,'endpoint'):
                    self.a.transitions(start,end)
            with self.assertRaisesRegex(Unsupported,'month-boundary'):
                self.a.month_boundaries(near,'amanta')
        for offset in (-1,1):
            result=self.a.tithi_interval(t+timedelta(seconds=offset))
            self.assertTrue(result['review_required'])

    def test_ambiguous_or_nonfinite_sample_motion_rejected(self):
        start=datetime(2026,1,1,tzinfo=UTC)
        for phase in (np.nan,np.inf):
            with patch.object(self.a,'_longitudes',return_value=(0.0,phase)):
                with self.assertRaises(Unsupported): self.a.elongation(start)
        with patch.object(self.a,'_elongation',side_effect=lambda ts:np.zeros_like(ts)):
            with self.assertRaises(Unsupported): self.a.transitions(start,start+timedelta(days=1))
        with self.assertRaises(Unsupported): self.a.transitions(start,start+timedelta(microseconds=1))

    def test_public_range_cannot_return_padded_interval_claims(self):
        for instant in (MINIMUM,MAXIMUM-timedelta(seconds=1)):
            self.assertIn(self.a.tithi_at(instant),range(1,31))
        with self.assertRaises(Unsupported): self.a.tithi_interval(MINIMUM)
        for instant in (MINIMUM,MAXIMUM-timedelta(seconds=1)):
            for convention in ('amanta','purnimanta'):
                with self.subTest(instant=instant,convention=convention),self.assertRaises(Unsupported):
                    self.a.month_boundaries(instant,convention)
        with self.assertRaises(Unsupported): self.a.at_sunrise(date(1900,1,1))
        self.assertEqual(self.a.at_sunrise(date(2100,12,31))['date'],'2100-12-31')

    def test_preview_range_end_sentinel_and_unrelated_padding(self):
        lower=self.a.monthly_preview(1,date(1900,1,2),date(1900,1,3))
        self.assertEqual([r['selected_date'] for r in lower],['1900-01-02'])
        upper=self.a.monthly_preview(1,date(2100,12,30),date(2101,1,1))
        self.assertEqual([r['selected_date'] for r in upper],['2100-12-31'])
        with self.assertRaises(Unsupported): self.a.monthly_preview(30,date(1900,1,1),date(1900,1,2))
        for start,end in ((date(1899,12,31),date(1900,1,2)),(date(2100,12,31),date(2101,1,2))):
            with self.assertRaises(Unsupported): self.a.monthly_preview(1,start,end)

    def test_transition_ranges_and_sunrise_are_consistent(self):
        for start,end in ((MINIMUM,MINIMUM+timedelta(days=2)),(MAXIMUM-timedelta(days=2),MAXIMUM)):
            rows=self.a.transitions(start,end)
            self.assertTrue(rows)
            self.assertTrue(all(start<datetime.fromisoformat(r['at'])<=end for r in rows))
        for day in (date(1899,12,31),date(2101,1,1)):
            with self.assertRaises(Unsupported): self.a.sunrise(day)
        self.assertTrue(MINIMUM<=self.a.sunrise(date(1900,1,1))<MAXIMUM)
        with self.assertRaises(Unsupported): self.a.sunrise(date(2026,1,1),[])
