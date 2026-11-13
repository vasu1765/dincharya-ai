"""Public-fixture research only; no scheduling, database or transport."""
from datetime import datetime,timedelta
import hashlib
import json
import os
from pathlib import Path
import socket
import unittest
from unittest.mock import patch
from prototypes.panchang.astronomy import Astronomy,Unsupported
from prototypes.panchang.month_research import MonthResearch,FIXTURES


class MonthResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=Astronomy(os.environ['DINCHARYA_PUBLIC_DE440S'])
        cls.model=MonthResearch(cls.a)
        cls.refs=json.loads(FIXTURES.read_text())

    @classmethod
    def tearDownClass(cls): cls.a.close()

    def test_accepted_evidence_bytes_preserved(self):
        for name,digest in self.refs['accepted_fixture_sha256'].items():
            self.assertEqual(hashlib.sha256(FIXTURES.with_name(name).read_bytes()).hexdigest(),digest)

    def test_selected_multiyear_labels_and_pakshas(self):
        for r in self.refs['cases']:
            for conv in ('amanta','purnimanta'):
                if r[conv] is None: continue
                with self.subTest(day=r['id'],convention=conv):
                    actual=self.model.candidate(datetime.fromisoformat(r['at']),conv)
                    self.assertEqual((actual['month'],actual['intercalation'],actual['ordinal']),
                                     (r[conv],r['intercalation'],r['ordinal']))
                    self.assertEqual(actual['paksha'],'shukla' if r['ordinal']<=15 else 'krishna')

    def test_new_public_boundary_fixtures_keep_sixty_second_gate(self):
        for r in self.refs['transitions']:
            at=datetime.fromisoformat(r['at'])
            rows=[row for row in self.a.transitions(at-timedelta(hours=1),at+timedelta(hours=1)) if row['ordinal']==r['ordinal']]
            self.assertEqual(len(rows),1)
            self.assertEqual(r['tolerance_seconds'],60)
            self.assertLessEqual(abs((datetime.fromisoformat(rows[0]['at'])-at).total_seconds()),60)

    def test_ordinary_shravana_halves_share_name_not_contiguous_bounds(self):
        first=self.model.candidate(datetime.fromisoformat('2023-07-10T06:00:00+00:00'))
        second=self.model.candidate(datetime.fromisoformat('2023-08-25T06:00:00+00:00'))
        self.assertEqual((first['month'],first['intercalation']),('shravana','ordinary'))
        self.assertEqual((first['month'],first['intercalation']),(second['month'],second['intercalation']))
        self.assertNotEqual(first['amanta_start'],second['amanta_start'])
        for day in ('2023-07-25','2023-08-10'):
            mid=self.model.candidate(datetime.fromisoformat(day+'T06:00:00+00:00'))
            self.assertEqual((mid['month'],mid['intercalation']),('shravana','adhika'))

    def test_lunar_year_token_transition_is_not_purnimanta_month_change(self):
        for r in self.refs['chaitra_anchor_cases']:
            self.assertEqual(self.model.chaitra_anchor_year(datetime.fromisoformat(r['at'])),r['expected_year'])
        for day in ('2024-04-08','2024-04-09'):
            self.assertEqual(self.model.candidate(datetime.fromisoformat(day+'T06:00:00+00:00'))['month'],'chaitra')

    def test_evidence_bounded_annual_examples(self):
        for r in self.refs['annual_examples']:
            with self.subTest(example=r['id']):
                actual=self.model.annual_example(r['year'],r['month'],r['ordinal'],r['intercalation'],r['convention'])
                self.assertEqual(actual['selected_date'],r['selected_date'])
                self.assertEqual(actual['sunrise_dates'],r['sunrise_dates'])
                self.assertFalse(actual['usable_for_scheduling'])
                if r['selected_date'] is None: self.assertEqual(actual['status'],'needs_review')
        ordinary=self.model.annual_example(2023,'shravana',9,'ordinary')
        adhika=self.model.annual_example(2023,'shravana',9,'adhika')
        self.assertNotEqual(ordinary['research_identity'],adhika['research_identity'])
        self.assertEqual(ordinary,self.model.annual_example(2023,'shravana',9,'ordinary'))

    def test_unreviewed_rule_year_and_changed_evidence_cannot_preview(self):
        for values in [(2026,'chaitra',9,'ordinary'),(2024,'shravana',9,'ordinary'),
                       (True,'chaitra',9,'ordinary'),(2023,'chaitra',True,'ordinary'),
                       (2023,'chaitra',9,'guess')]:
            with self.assertRaises(Unsupported): self.model.annual_example(*values)
        with patch.object(self.a,'monthly_preview',return_value=[]),self.assertRaises(Unsupported):
            self.model.annual_example(2023,'chaitra',9,'ordinary')
        # A newly discrepant occurrence cannot be replaced by the stored date.
        with patch.object(self.a,'monthly_preview',return_value=[dict(start='2023-03-29T12:00:00+00:00',
                end='2023-03-30T18:00:00+00:00',selected_date='2023-03-31',sunrise_dates=['2023-03-31'])]),self.assertRaises(Unsupported):
            self.model.annual_example(2023,'chaitra',9,'ordinary')

    def test_numerical_month_transitions_and_kshaya_fail_closed(self):
        for r in self.refs['unsupported_cases']:
            for conv in ('amanta','purnimanta'):
                with self.assertRaisesRegex(Unsupported,'Kshaya'):
                    self.model.candidate(datetime.fromisoformat(r['at']),conv)
        # Numerical exact and near full/new moon must not guess the month side.
        for n in (1,16):
            row=next(r for r in self.a.transitions(datetime.fromisoformat('2023-07-01T00:00:00+00:00'),
                     datetime.fromisoformat('2023-08-01T00:00:00+00:00')) if r['ordinal']==n)
            at=datetime.fromisoformat(row['at'])
            for offset in (-.01,0,.01):
                with self.assertRaises(Unsupported): self.model.candidate(at+timedelta(seconds=offset))
        for at in ('1899-12-31T00:00:00+00:00','2101-01-01T00:00:00+00:00'):
            with self.assertRaises(Unsupported): self.model.candidate(datetime.fromisoformat(at))

    def test_offline_and_public_scheduling_apis_remain_disabled(self):
        with patch.object(socket.socket,'connect',side_effect=AssertionError('No network')):
            self.assertEqual(self.model.candidate(datetime.fromisoformat('2024-04-17T06:00:00+00:00'))['month'],'chaitra')
        with self.assertRaises(Unsupported): self.a.annual_preview(month='chaitra',ordinal=9)
        with self.assertRaises(Unsupported): self.a.month_label(datetime.fromisoformat('2024-04-17T06:00:00+00:00'))
        with self.assertRaises(Unsupported): self.model.candidate(datetime.fromisoformat('2024-04-17T06:00:00+00:00'),'unknown')
