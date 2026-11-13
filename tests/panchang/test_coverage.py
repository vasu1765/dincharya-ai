"""All-name evidence, profile-independent identity and conservative date guards."""
from copy import deepcopy
from datetime import date,datetime,timedelta
import json,os,unittest
from pathlib import Path
from unittest.mock import patch
from prototypes.panchang.astronomy import Astronomy,Unsupported,UTC
from prototypes.panchang.recurrence import RecurrenceResearch,LunarRule,lunation_cycle,reconcile_calculations,logical_key


class CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=Astronomy(os.environ['DINCHARYA_PUBLIC_DE440S'])
        cls.refs=json.loads(Path('prototypes/panchang/coverage-references.json').read_text())
        cls.m=RecurrenceResearch(cls.a)

    @classmethod
    def tearDownClass(cls):cls.a.close()

    def test_all_names_and_both_pakshas_against_PAC(self):
        labels=set()
        for r in self.refs['cases']:
            t=datetime.fromisoformat(r['at'])
            self.assertEqual(self.a.tithi_at(t),r['ordinal'])
            for convention in ('amanta','purnimanta'):
                actual=self.m._label(t,r['ordinal'],convention)
                self.assertEqual(actual['month'],r[convention],r['id'])
                self.assertTrue(actual['supported'])
            labels.add((r['amanta'],r['paksha']))
        self.assertEqual(len(labels),24)

    def test_direct_Purnimanta_labels_for_five_new_names(self):
        for r in self.refs['direct_purnimanta']:
            at=datetime.fromisoformat(r['at']);ordinal=self.a.tithi_at(at)
            self.assertEqual(self.m._label(at,ordinal,'purnimanta')['month'],r['purnimanta'])
            self.assertEqual(self.m._label(at,ordinal,'amanta')['month'],r['amanta'])

    def test_logical_identity_ignores_profile_date_and_policy(self):
        rule=LunarRule('shukla',9,'ordinary',month='chaitra')
        first=RecurrenceResearch(self.a).annual(rule,2026)
        other=RecurrenceResearch(self.a,'pac_47_hypothesis').annual(rule,2026)
        self.assertNotEqual(first['profile'],other['profile'])
        self.assertEqual(first['occurrences'][0]['identity'],other['occurrences'][0]['identity'])
        self.assertNotIn('profile',first['occurrences'][0]['identity'])
        changed=deepcopy(other);changed['occurrences'][0]['selected_date']='2026-03-26'
        reconciled=reconcile_calculations(first,changed)
        self.assertEqual(len(reconciled['occurrences']),1)
        self.assertIsNone(reconciled['occurrences'][0]['selected_date'])
        self.assertEqual(reconciled['occurrences'][0]['reason'],'calculation_date_disagreement')

    def test_duplicate_and_legacy_cycle_changes_require_review(self):
        sample=self.m.preview(LunarRule('shukla',9,'ordinary',month='chaitra'),date(2024,4,15),date(2024,4,20))
        duplicate=deepcopy(sample);duplicate['occurrences']*=2
        with self.assertRaises(Unsupported):reconcile_calculations(sample,duplicate)
        for value in (None,dict(version=1),dict(sample['occurrences'][0]['identity'],profile='extra')):
            with self.assertRaises(Unsupported):logical_key(value)
        changed=deepcopy(sample);changed['occurrences'][0]['identity']['lunation_cycle']+=1
        with self.assertRaises(Unsupported):reconcile_calculations(sample,changed)
        for hours in (-8,8):self.assertEqual(lunation_cycle(datetime(2000,1,6,18,14,tzinfo=UTC)+timedelta(hours=hours)),0)
        with self.assertRaises(Unsupported):lunation_cycle(datetime(2000,1,20,tzinfo=UTC))

    def test_documented_300_second_guard_in_actual_preview(self):
        model=RecurrenceResearch(self.a)
        row=next(r for r in self.a.transitions(datetime(2023,3,29,tzinfo=UTC),datetime(2023,3,31,tzinfo=UTC)) if r['ordinal']==9)
        at=datetime.fromisoformat(row['at'])
        with patch.object(model,'_dawn',return_value=at+timedelta(seconds=240)):
            rows=model.preview(LunarRule('shukla',9,'ordinary',month='chaitra',repeated='first'),date(2023,3,29),date(2023,3,31))['occurrences']
        self.assertTrue(rows)
        self.assertTrue(all(r['selected_date'] is None and r['reason']=='boundary_uncertainty' for r in rows))

    def test_cycle_count_unique_across_range(self):
        for year in (1901,2000,2023,2099):
            roots=self.a.transitions(datetime(year,1,1,tzinfo=UTC),datetime(year+1,1,1,tzinfo=UTC))
            cycles=[lunation_cycle(datetime.fromisoformat(r['at'])) for r in roots if r['ordinal']==1]
            self.assertGreaterEqual(len(cycles),12)
            self.assertTrue(all(b==a+1 for a,b in zip(cycles,cycles[1:])))

    def test_deliberately_near_sunrise_against_PAC_instant(self):
        ref=self.refs['near_sunrise'];at=datetime.fromisoformat(ref['published_transition'])
        for model in ('upper_limb_50','pac_47_hypothesis'):
            dawn=self.a.sunrise(date.fromisoformat(ref['day']),model)
            # PAC geocentric boundary compared with DELHI, not PAC station sunrise.
            self.assertEqual(self.a.tithi_at(dawn),ref['ending_ordinal'])
            self.assertGreater((at-dawn).total_seconds(),300)
            self.assertLess((at-dawn).total_seconds(),900)
