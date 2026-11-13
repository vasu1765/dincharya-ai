"""Bounded personal recurrence pre-integration assessment, public/synthetic only."""
from copy import deepcopy
from datetime import datetime,date,timedelta
import hashlib,json,os,unittest,time,socket
from pathlib import Path
from unittest.mock import patch
from prototypes.panchang.astronomy import Astronomy,UTC,Unsupported
from prototypes.panchang.recurrence import RecurrenceResearch,LunarRule,lunation_cycle,logical_key,reconcile_calculations


class PreintegrationTests(unittest.TestCase):
    evidence={}

    @classmethod
    def setUpClass(cls):
        cls.a=Astronomy(os.environ['DINCHARYA_PUBLIC_DE440S'])
        cls.m=RecurrenceResearch(cls.a)

    @classmethod
    def tearDownClass(cls):cls.a.close()

    def sample(self):
        return self.m.preview(LunarRule('shukla',9,'ordinary',month='shravana'),date(2023,8,23),date(2023,8,28))

    def test_reconciliation_refuses_application_state(self):
        sample=self.sample()
        for field,value in [('approved',True),('delivery_status','sent'),('delivery_status','uncertain'),('series_id','synthetic-series')]:
            prior=deepcopy(sample);prior['occurrences'][0][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(Unsupported):reconcile_calculations(prior,sample)
        self.evidence['application_boundary']='approved/sent/uncertain/series payloads rejected; no ledger or transport capability'

    def test_cycle_identity_whole_range_and_midnight(self):
        epoch=datetime(2000,1,6,18,14,tzinfo=UTC);spacing=timedelta(days=29.530588861);count=0
        for n in range(-1300,1301):
            t=epoch+n*spacing
            if 1900<=t.year<=2100:
                for hours in (-8,8):
                    moved=t+timedelta(hours=hours)
                    if 1900<=moved.year<=2100:self.assertEqual(lunation_cycle(moved),n)
                count+=1
        actual=[]
        for year in (1900,1950,2050,2100):
            roots=self.a.transitions(datetime(year,1,1,tzinfo=UTC),datetime(year+1,1,1,tzinfo=UTC))
            cycles=[lunation_cycle(datetime.fromisoformat(r['at'])) for r in roots if r['ordinal']==1]
            self.assertTrue(all(b==a+1 for a,b in zip(cycles,cycles[1:])))
            actual.append(dict(year=year,count=len(cycles)))
        self.evidence['cycles']=dict(analytical_centers=count,jitter_hours=8,actual_new_moon_years=actual)

    def test_ordinary_adhika_and_both_annual_policies(self):
        outputs={}
        for year in (2023,2024):
            for choice in ('ordinary','adhika','both'):
                result=self.m.annual(LunarRule('shukla',9,choice,month='shravana'),year)
                outputs[f'{year}-{choice}']=result['occurrences']
        ordinary=outputs['2023-ordinary'];adhika=outputs['2023-adhika'];both=outputs['2023-both']
        self.assertEqual([r['selected_date'] for r in ordinary],['2023-08-25'])
        self.assertEqual([r['selected_date'] for r in adhika],['2023-07-27'])
        self.assertEqual({logical_key(r['identity']) for r in both},{logical_key(r['identity']) for r in ordinary+adhika})
        self.assertEqual(outputs['2024-adhika'],[])
        self.assertEqual(len(outputs['2024-ordinary']),1)
        self.evidence['annual_intercalation']=outputs

    def test_birthday_and_anniversary_interpretation(self):
        observation=datetime.fromisoformat('2023-04-03T04:30:00+00:00')
        instant=self.m.from_birth(observation,basis='instant');sunrise=self.m.from_birth(observation,basis='sunrise')
        self.assertEqual((instant.tithi,sunrise.tithi),(13,12))
        # Birthday/wedding semantics do not alter a calendar rule. Future series
        # IDs must distinguish two user events that share this calendar key.
        birthday=self.sample();wedding=self.sample()
        self.assertEqual(birthday['occurrences'][0]['identity'],wedding['occurrences'][0]['identity'])
        self.assertNotIn('series_id',birthday['occurrences'][0]['identity'])
        self.evidence['personal_policy']=dict(instant_day=instant.tithi,sunrise_day=sunrise.tithi,
            distinct_series_required=True,recurrence_assignment='sunrise',no_private_birth_record=True)

    def test_repeated_skipped_and_public_reference_subset(self):
        refs=json.loads(Path('prototypes/panchang/calendar-references.json').read_text())
        checks=[]
        for ref in refs['selection_cases']:
            for policy in ('review','first','last'):
                result=self.m.preview(LunarRule(ref['paksha'],ref['tithi'],ref['intercalation'],month=ref['month'],repeated=policy),
                    *[date.fromisoformat(x) for x in ref['window']])
                row=result['occurrences'][0]
                self.assertEqual(row['sunrise_dates'],ref['sunrise_dates'])
                self.assertEqual(row['selected_date'],None if policy=='review' else ref[policy])
                checks.append(dict(reference=ref['id'],policy=policy,actual=row))
        self.evidence['repeat_skip']=checks

    def test_profile_matching_cannot_lose_or_duplicate_occurrences(self):
        prior=self.sample();other=RecurrenceResearch(self.a,'pac_47_hypothesis').preview(
            LunarRule('shukla',9,'ordinary',month='shravana'),date(2023,8,23),date(2023,8,28))
        self.assertEqual(prior['occurrences'][0]['identity'],other['occurrences'][0]['identity'])
        self.assertNotEqual(prior['profile'],other['profile'])
        unchanged=deepcopy(prior);reconcile_calculations(prior,other);self.assertEqual(prior,unchanged)
        for alteration in ('lost','duplicate','new','renamed'):
            changed=deepcopy(other)
            if alteration=='lost':changed['occurrences']=[]
            elif alteration=='duplicate':changed['occurrences']*=2
            elif alteration=='new':
                extra=deepcopy(changed['occurrences'][0]);extra['identity']['lunation_cycle']+=1;changed['occurrences'].append(extra)
            else:changed['occurrences'][0]['identity']['month']='kartika'
            with self.subTest(alteration=alteration),self.assertRaises(Unsupported):reconcile_calculations(prior,changed)
        changed=deepcopy(other);changed['occurrences'][0]['selected_date']='2023-08-24'
        held=reconcile_calculations(prior,changed)
        self.assertIsNone(held['occurrences'][0]['selected_date'])
        self.assertFalse(held['usable_for_scheduling'])
        self.evidence['matching']=dict(same_identity=True,date_change_withheld=True,lost_duplicate_new_renamed_rejected=True,prior_immutable=True)

    def test_split_purnimanta_and_amanta_boundary(self):
        rows=[]
        for paksha,flag,day in [('krishna','ordinary','2023-07-04'),('shukla','adhika','2023-07-18'),('krishna','adhika','2023-08-02'),('shukla','ordinary','2023-08-17')]:
            start=date.fromisoformat(day)
            row=self.m.preview(LunarRule(paksha,1,flag,month='shravana'),start,start+timedelta(days=2))['occurrences'][0]
            rows.append(row)
        self.assertEqual(rows[0]['identity']['lunation_cycle'],rows[3]['identity']['lunation_cycle'])
        self.assertEqual(rows[1]['identity']['lunation_cycle'],rows[2]['identity']['lunation_cycle'])
        self.assertNotEqual(rows[0]['identity']['lunation_cycle'],rows[1]['identity']['lunation_cycle'])
        am=self.m.preview(LunarRule('krishna',1,'ordinary',convention='amanta',month='ashadha'),date(2023,7,4),date(2023,7,6))['occurrences'][0]
        self.assertEqual(am['selected_date'],rows[0]['selected_date'])
        self.assertNotEqual(logical_key(am['identity']),logical_key(rows[0]['identity']))
        self.evidence['purnimanta_split']=rows

    def test_bounded_near_sunrise_and_unsupported_cases(self):
        ref=json.loads(Path('prototypes/panchang/coverage-references.json').read_text())['near_sunrise'];near=[]
        for horizon in ('upper_limb_50','pac_47_hypothesis'):
            model=RecurrenceResearch(self.a,horizon)
            dawn=self.a.sunrise(date(2024,5,1),horizon)
            gap=(datetime.fromisoformat(ref['published_transition'])-dawn).total_seconds()
            row=model.preview(LunarRule('krishna',7,'ordinary',convention='amanta',month='chaitra'),date(2024,4,30),date(2024,5,2))['occurrences'][0]
            self.assertEqual(row['selected_date'],'2024-05-01');self.assertGreater(gap,300)
            near.append(dict(horizon=horizon,gap_seconds=gap,selected_date=row['selected_date']))
        kshaya=self.m.preview(LunarRule('shukla',9,'both'),date(1983,1,15),date(1983,2,12))
        self.assertTrue(kshaya['occurrences']);self.assertTrue(all(r['selected_date'] is None for r in kshaya['occurrences']))
        root=next(r for r in self.a.transitions(datetime(2023,3,29,tzinfo=UTC),datetime(2023,3,31,tzinfo=UTC)) if r['ordinal']==9)
        model=RecurrenceResearch(self.a)
        with patch.object(model,'_dawn',return_value=datetime.fromisoformat(root['at'])+timedelta(seconds=240)):
            uncertain=model.preview(LunarRule('shukla',9,'ordinary',month='chaitra',repeated='first'),date(2023,3,29),date(2023,3,31))
        self.assertTrue(all(r['selected_date'] is None for r in uncertain['occurrences']))
        self.evidence['near_sunrise']=near;self.evidence['unsupported']=dict(kshaya_withheld=True,guard_240_seconds_withheld=True)

    def test_offline_cache_budget(self):
        model=RecurrenceResearch(self.a);rule=LunarRule('shukla',9,'ordinary',month='chaitra')
        with patch.object(socket.socket,'connect',side_effect=AssertionError('No external calls')):
            begin=time.perf_counter();first=model.annual(rule,2026);cold=time.perf_counter()-begin
            misses=model.month_misses;begin=time.perf_counter();again=model.annual(rule,2026);warm=time.perf_counter()-begin
        self.assertEqual(first,again);self.assertEqual(misses,model.month_misses)
        self.assertLessEqual(len(model._months),32);self.assertLessEqual(len(model._previews),8)
        self.assertLessEqual(len(self.a._sunrises),800)
        self.evidence['performance']=dict(cold_month_cache_seconds=cold,warm_seconds=warm,
            month_entries=len(model._months),preview_entries=len(model._previews),warm_month_calculations=0,
            caveat='Shared astronomy sunrise cache may be warm; development host, not VPS certification')

    def test_changed_personal_policy_requires_review_even_same_date(self):
        prior=self.sample()
        for change in ('birth_basis','repeated'):
            current=deepcopy(prior)
            if change=='birth_basis':current['birth_basis']='sunrise'
            else:current['occurrences'][0]['selection_policy']['repeated']='first'
            result=reconcile_calculations(prior,current)
            self.assertEqual(result['occurrences'][0]['identity'],prior['occurrences'][0]['identity'])
            self.assertIsNone(result['occurrences'][0]['selected_date'])
            self.assertEqual(result['occurrences'][0]['reason'],'recurrence_policy_disagreement')
