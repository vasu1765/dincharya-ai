"""Focused general research preview/identity/date-gate regressions."""
from copy import deepcopy
from datetime import date,datetime,timedelta
import hashlib
import json
import os
from pathlib import Path
import socket
import unittest
from unittest.mock import patch
from prototypes.panchang.astronomy import Astronomy,Unsupported,DELHI
from prototypes.panchang.recurrence import RecurrenceResearch,LunarRule,DATE_GUARD_SECONDS


class RecurrenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=Astronomy(os.environ['DINCHARYA_PUBLIC_DE440S'])
        cls.refs=json.loads(Path('prototypes/panchang/calendar-references.json').read_text())

    @classmethod
    def tearDownClass(cls):cls.a.close()

    def setUp(self):self.m=RecurrenceResearch(self.a)

    def test_original_evidence_unchanged(self):
        for name,digest in self.refs['accepted_sha256'].items():
            self.assertEqual(hashlib.sha256(Path('prototypes/panchang',name).read_bytes()).hexdigest(),digest)

    def test_arbitrary_annual_rule_without_fixture_lookup(self):
        rule=LunarRule('shukla',9,'ordinary',month='chaitra')
        with patch('pathlib.Path.read_text',side_effect=AssertionError('No fixture lookup')):
            result=self.m.annual(rule,2026)
        self.assertEqual(len(result['occurrences']),1)
        row=result['occurrences'][0]
        self.assertIsNotNone(row['selected_date'])
        self.assertFalse(result['usable_for_scheduling'])
        self.assertEqual(row['identity']['tithi'],9)

    def test_monthly_enumeration_and_unvalidated_names_withheld(self):
        result=self.m.monthly(LunarRule('shukla',3,'both'),date(2024,1,1),date(2025,1,1))
        self.assertGreaterEqual(len(result['occurrences']),12)
        self.assertFalse(any(r['reason']=='unsupported_month_name' for r in result['occurrences']))
        named=self.m.annual(LunarRule('shukla',3,'ordinary',month='kartika'),2024)
        self.assertTrue(named['occurrences'])
        self.assertTrue(all(r['selected_date'] is not None for r in named['occurrences']))
        # Preserve the fail-closed behavior if any future scope lacks support.
        with patch('prototypes.panchang.recurrence.RESEARCH_NAMES',frozenset(('chaitra',))):
            restricted=RecurrenceResearch(self.a)
            rows=restricted.annual(LunarRule('shukla',3,'ordinary',month='kartika'),2024)['occurrences']
            self.assertTrue(rows)
            self.assertTrue(all(r['selected_date'] is None and r['identity'] is None for r in rows))

    def test_purnimanta_canonical_anchor_skips_adjacent_adhika(self):
        anchors={}
        for paksha,flag,monthday in [('krishna','ordinary','2023-07-04'),('shukla','ordinary','2023-08-17'),
                                    ('shukla','adhika','2023-07-18'),('krishna','adhika','2023-08-02')]:
            day=date.fromisoformat(monthday)
            rows=self.m.preview(LunarRule(paksha,1,flag,month='shravana'),day-timedelta(days=1),day+timedelta(days=2))['occurrences']
            self.assertEqual(len(rows),1)
            anchors[(paksha,flag)]=rows[0]['identity']['lunation_cycle']
        self.assertEqual(anchors[('krishna','ordinary')],anchors[('shukla','ordinary')])
        self.assertEqual(anchors[('krishna','adhika')],anchors[('shukla','adhika')])
        self.assertNotEqual(anchors[('krishna','ordinary')],anchors[('krishna','adhika')])

    def test_repeated_policy_and_skipped_cases_against_calendar(self):
        for ref in self.refs['selection_cases']:
            start,end=[date.fromisoformat(d) for d in ref['window']]
            for policy in ('review','first','last'):
                rule=LunarRule(ref['paksha'],ref['tithi'],ref['intercalation'],month=ref['month'],repeated=policy)
                row=self.m.preview(rule,start,end)['occurrences'][0]
                self.assertEqual(row['sunrise_dates'],ref['sunrise_dates'])
                self.assertEqual(row['selected_date'],None if policy=='review' else ref[policy])
                if not ref['sunrise_dates']:self.assertEqual(row['reason'],'skipped_at_sunrise')

    def test_identity_window_and_policy_independence(self):
        ids=[]
        for policy,start,end in [('first',date(2023,4,1),date(2023,4,5)),('last',date(2023,4,3),date(2023,4,4))]:
            fresh=RecurrenceResearch(self.a)
            row=fresh.preview(LunarRule('shukla',12,'ordinary',month='chaitra',repeated=policy),start,end)['occurrences'][0]
            ids.append(row['identity'])
        self.assertEqual(ids[0],ids[1])
        with self.assertRaises(Unsupported):
            LunarRule('shukla',True,'ordinary')
        # First-policy occurrence is not reassigned to its second sunrise by clipping.
        empty=self.m.preview(LunarRule('shukla',12,'ordinary',month='chaitra',repeated='first'),date(2023,4,3),date(2023,4,4))
        self.assertEqual(empty['occurrences'],[])

    def test_instant_and_sunrise_birth_rule_are_distinct(self):
        birth=datetime.fromisoformat('2023-04-03T04:30:00+00:00')
        instant=self.m.from_birth(birth,basis='instant')
        sunrise=self.m.from_birth(birth,basis='sunrise')
        self.assertEqual((instant.tithi,sunrise.tithi),(13,12))
        self.assertEqual((instant.birth_basis,sunrise.birth_basis),('instant','sunrise'))
        self.assertEqual(instant,self.m.from_birth(birth.astimezone(DELHI),basis='instant'))
        with self.assertRaises(Unsupported):self.m.from_birth(birth,basis='guess')

    def test_independent_sunrise_date_gate_selected_days(self):
        for ref in self.refs['calendar_days']:
            for model in ('upper_limb_50','pac_47_hypothesis'):
                observed=self.a.at_sunrise(date.fromisoformat(ref['day']),model)
                self.assertEqual(observed['ordinal'],ref['ordinal'])
                dawn=datetime.fromisoformat(observed['sunrise'])
                gap=min((dawn-datetime.fromisoformat(observed['start'])).total_seconds(),
                        (datetime.fromisoformat(observed['end'])-dawn).total_seconds())
                self.assertGreater(gap,DATE_GUARD_SECONDS)

    def test_uncertain_sunrise_and_birth_never_select(self):
        row=self.a.transitions(datetime.fromisoformat('2023-03-29T00:00:00+00:00'),datetime.fromisoformat('2023-03-31T00:00:00+00:00'))[0]
        at=datetime.fromisoformat(row['at'])
        with self.assertRaises(Unsupported):self.m.from_birth(at+timedelta(seconds=1),basis='instant')
        # Explicit injected dawn 10 seconds after a real tithi transition.
        rule=LunarRule('shukla',9,'ordinary',month='chaitra')
        with patch.object(self.m,'_dawn',return_value=at+timedelta(seconds=10)):
            rows=self.m.preview(rule,date(2023,3,29),date(2023,3,31))['occurrences']
        self.assertTrue(rows)
        self.assertTrue(all(r['selected_date'] is None for r in rows))

    def test_kshaya_and_range_fail_closed(self):
        result=self.m.preview(LunarRule('shukla',9,'both'),date(1983,1,15),date(1983,2,12))
        self.assertTrue(result['occurrences'])
        self.assertTrue(all(r['selected_date'] is None for r in result['occurrences']))
        for start,end in [(date(1899,1,1),date(1900,1,1)),(date(2100,12,31),date(2101,1,2)),
                          (date(2023,1,1),date(2025,1,1))]:
            with self.assertRaises(Unsupported):self.m.preview(LunarRule('shukla',1,'both'),start,end)
        with self.assertRaises(Unsupported):self.m.annual(LunarRule('shukla',1,'both'),2023)

    def test_bounded_copy_safe_caches_and_profile_invalidation(self):
        rule=LunarRule('shukla',9,'ordinary',month='chaitra')
        a=self.m.annual(rule,2024);original=deepcopy(a)
        a['occurrences'][0]['selected_date']='invented'
        self.assertEqual(self.m.annual(rule,2024),original)
        self.assertEqual(self.m.preview_hits,1)
        for year in (2022,2023,2025):self.m.annual(rule,year)
        self.assertLessEqual(len(self.m._months),32)
        for day in range(1,11):self.m.preview(rule,date(2024,4,day),date(2024,4,day+1))
        self.assertLessEqual(len(self.m._previews),8)
        other=RecurrenceResearch(self.a,'pac_47_hypothesis')
        self.assertNotEqual(self.m.profile,other.profile)
        with patch.object(self.a,'latitude',0),self.assertRaises(Unsupported):self.m.annual(rule,2024)
        self.assertEqual(len(self.m._previews),0)
        other.profile='changed'
        with self.assertRaises(Unsupported):other.annual(rule,2024)

    def test_offline_and_no_scheduling_approval(self):
        with patch.object(socket.socket,'connect',side_effect=AssertionError('No network')):
            result=self.m.annual(LunarRule('krishna',7,'ordinary',month='chaitra'),2024)
        self.assertEqual(result['calendar_date_gate'],'not_adopted')
        self.assertFalse(result['usable_for_scheduling'])
        with self.assertRaises(Unsupported):self.a.annual_preview(month='chaitra',ordinal=9)
