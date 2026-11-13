"""Synthetic offline personal-series proposal/approval/ledger acceptance."""
from copy import deepcopy
from dataclasses import FrozenInstanceError,replace
from datetime import date,datetime,timedelta
import json,os,unittest
from pathlib import Path
from uuid import UUID
from unittest.mock import patch
from dincharya.reminders import DeliveryReceipt
from prototypes.panchang.astronomy import Astronomy,Unsupported
from prototypes.panchang.recurrence import LunarRule,RecurrenceResearch,reconcile_calculations
from prototypes.panchang.memory_contract import MemoryContract,Series,FixtureHistory,ContractDenied


class MemoryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixtures=json.loads(Path('tests/panchang/fixtures/memory-contract.synthetic.json').read_text())

    def setUp(self):
        self.owner=object();self.c=MemoryContract(owner_capability=self.owner)
        self.series=[Series(UUID(r['series_id']),r['kind']) for r in self.fixtures['series']]
        for series in self.series:self.c.register(series)
        self.rule=LunarRule('shukla',9,'ordinary',month='shravana')
        self.preview=deepcopy(self.fixtures['ordinary']);self.n=0

    def submit(self,preview=None,rule=None,series=0):
        return self.c.submit(self.series[series].series_id,rule or self.rule,self.preview if preview is None else preview)

    def approve(self,p,review=False):
        self.n+=1
        return self.c.approve(p.proposal_id,principal=self.owner,action_id=UUID(int=100+self.n),acknowledge_changes=review)

    def changed_date(self):
        value=deepcopy(self.preview);row=value['occurrences'][0]
        # A synthetic alternate calculation shifts both selected and sunrise date.
        row['selected_date']='2023-08-26';row['sunrise_dates']=['2023-08-26']
        for field in ('start','end'):row[field]=(datetime.fromisoformat(row[field])+timedelta(days=1)).isoformat()
        return value

    def test_unapproved_cannot_materialize(self):
        p=self.submit()[0]
        with self.assertRaises(ContractDenied):self.c.materialize(p.proposal_id)
        self.assertEqual(self.c.entries(),())

    def test_repeat_submission_and_decision_replay_idempotent(self):
        p=self.submit()[0];self.assertEqual(self.submit()[0],p)
        approval=self.c.approve(p.proposal_id,principal=self.owner,action_id=UUID(int=11))
        self.assertEqual(self.c.approve(p.proposal_id,principal=self.owner,action_id=UUID(int=11)),approval)
        first=self.c.materialize(p.proposal_id)
        self.assertEqual(self.c.materialize(p.proposal_id),first)
        self.assertEqual(len(self.c.entries()),1)

    def test_same_identity_date_recalculation_and_overlap_do_not_duplicate(self):
        p=self.submit()[0];self.approve(p);old=self.c.materialize(p.proposal_id)
        overlapping=deepcopy(self.preview)
        overlapping['occurrences'][0]['start']='2023-08-24T22:19:00+00:00'
        self.assertEqual(self.submit(overlapping)[0],p)
        updated=deepcopy(self.preview);updated['profile']+='/synthetic-recalculation'
        updated['occurrences'][0]['provenance']['profile']=updated['profile']
        new=self.submit(updated)[0];self.approve(new,True)
        self.assertEqual(self.c.materialize(new.proposal_id),old)
        self.assertEqual(len(self.c.entries()),1)
        self.assertEqual(old.approval.snapshot_json,p.snapshot_json)

    def test_changed_date_is_reviewed_but_never_replaces_approved_entry(self):
        p=self.submit()[0];self.approve(p);old=self.c.materialize(p.proposal_id)
        changed=self.submit(self.changed_date())[0]
        self.assertTrue(changed.requires_review)
        with self.assertRaises(ContractDenied):self.approve(changed)
        self.approve(changed,True)
        with self.assertRaises(ContractDenied):self.c.materialize(changed.proposal_id)
        self.assertEqual(self.c.entries(),(old,))

    def test_birth_interpretation_and_repetition_need_fresh_approval(self):
        for field,value in [('birth_basis','sunrise'),('repeated','first')]:
            with self.subTest(field=field):
                # Each changed rule is a new candidate generation, not inherited approval.
                p=self.submit()[0]
                if p.proposal_id not in self.c._approvals:self.approve(p,True)
                rule=replace(self.rule,**{field:value});preview=deepcopy(self.preview)
                preview['birth_basis']=rule.birth_basis
                preview['occurrences'][0]['selection_policy']['repeated']=rule.repeated
                new=self.submit(preview,rule)[0]
                self.assertNotEqual(p.proposal_id,new.proposal_id)
                with self.assertRaises(ContractDenied):self.c.materialize(new.proposal_id)
                with self.assertRaises(ContractDenied):self.c.materialize(p.proposal_id)
                self.approve(new,True)
                # Ledger replacement is deliberately unsupported if an older rule exists.
                if not self.c.entries():self.c.materialize(new.proposal_id)

    def test_two_series_with_same_tithi_remain_separate(self):
        for series in (0,1):
            p=self.submit(series=series)[0];self.approve(p);self.c.materialize(p.proposal_id)
        a,b=self.c.entries();self.assertNotEqual(a.series_id,b.series_id);self.assertEqual(a.calendar_key,b.calendar_key)
        with self.assertRaises(ContractDenied):self.c.register(Series(a.series_id,'wedding_anniversary'))

    def test_sent_uncertain_history_and_receipts_never_change_or_resend(self):
        originals=[]
        for i,state in enumerate(('sent','uncertain')):
            p=self.submit(series=i)[0];self.approve(p);entry=self.c.materialize(p.proposal_id)
            h=FixtureHistory(UUID(int=400+i),state,DeliveryReceipt(12345,77) if state=='sent' else None)
            self.c.seed_history_for_test(entry.series_id,entry.calendar_key,h,principal=self.owner)
            originals.append(entry)
        history=self.c.histories();approvals=self.c.approvals()
        for i in (0,1):
            same=self.submit(series=i)[0];self.assertEqual(self.c.materialize(same.proposal_id),originals[i])
            changed=self.submit(self.changed_date(),series=i)[0];self.approve(changed,True)
            with self.assertRaises(ContractDenied):self.c.materialize(changed.proposal_id)
        self.assertEqual(self.c.histories(),history);self.assertEqual(self.c.entries(),tuple(originals))
        self.assertEqual(self.c.approvals()[:2],approvals)
        self.assertFalse(hasattr(self.c,'send'));self.assertFalse(hasattr(self.c,'claim'))
        with self.assertRaises(ContractDenied):self.c.seed_history_for_test(originals[0].series_id,originals[0].calendar_key,
            FixtureHistory(UUID(int=900),'uncertain'),principal=self.owner)

    def test_invalid_unselected_ambiguous_batch_is_atomic(self):
        for mutation in ('none','review','unsupported','skipped','mismatch','duplicate'):
            preview=deepcopy(self.preview);row=preview['occurrences'][0]
            if mutation=='none':row['selected_date']=None
            elif mutation=='review':row['status']='needs_review'
            elif mutation=='unsupported':row['identity']=None
            elif mutation=='skipped':row['sunrise_dates']=[]
            elif mutation=='mismatch':row['identity']['month']='kartika'
            else:preview['occurrences']*=2
            with self.subTest(mutation=mutation),self.assertRaises(ContractDenied):self.submit(preview)
            self.assertEqual(len(self.c._proposals),0);self.assertEqual(self.c.entries(),())
        self.assertEqual(self.submit(dict(self.preview,occurrences=[])),())

    def test_approval_scoped_to_single_occurrence_and_rule(self):
        both=deepcopy(self.fixtures['both']);rule=replace(self.rule,intercalation='both')
        p,q=self.submit(both,rule);self.approve(p)
        self.c.materialize(p.proposal_id)
        with self.assertRaises(ContractDenied):self.c.materialize(q.proposal_id)
        self.assertEqual(len(self.c.entries()),1)
        self.assertNotEqual(p.calendar_key,q.calendar_key)

    def test_authorization_replay_and_stale_snapshot_ABA(self):
        p=self.submit()[0];action=UUID(int=91)
        with self.assertRaises(ContractDenied):self.c.approve(p.proposal_id,principal=object(),action_id=action)
        self.c.approve(p.proposal_id,principal=self.owner,action_id=action)
        q=self.submit(self.changed_date())[0]
        with self.assertRaises(ContractDenied):self.c.approve(q.proposal_id,principal=self.owner,action_id=action,acknowledge_changes=True)
        again=self.submit()[0];self.assertNotEqual(again.proposal_id,p.proposal_id)
        replay=self.c.approve(p.proposal_id,principal=self.owner,action_id=action)
        self.assertEqual(replay.snapshot_json,p.snapshot_json)
        with self.assertRaises(ContractDenied):self.c.approve(p.proposal_id,principal=object(),action_id=action)
        with self.assertRaises(ContractDenied):self.c.materialize(p.proposal_id)
        with self.assertRaises(ContractDenied):self.approve(q,True)
        self.approve(again,True);self.c.materialize(again.proposal_id)

    def test_snapshots_and_returned_entries_immutable(self):
        p=self.submit()[0];snapshot=p.snapshot_json
        self.preview['occurrences'][0]['selected_date']='changed'
        self.approve(p);entry=self.c.materialize(p.proposal_id)
        self.assertEqual(entry.approval.snapshot_json,snapshot)
        for obj,field,value in [(p,'selected_date','changed'),(entry,'selected_date','changed'),(entry.approval,'snapshot_json','changed')]:
            with self.assertRaises(FrozenInstanceError):setattr(obj,field,value)

    def test_application_payload_cannot_enter_research_reconciliation(self):
        p=self.submit()[0];self.approve(p);entry=self.c.materialize(p.proposal_id)
        with self.assertRaises(Unsupported):reconcile_calculations({'occurrences':[entry]},self.preview)
        app=deepcopy(self.preview);app['occurrences'][0]['approval']=entry.approval
        with self.assertRaises(Unsupported):reconcile_calculations(app,self.preview)

    def test_actual_engine_to_adapter_without_network(self):
        with patch('socket.socket.connect',side_effect=AssertionError('No network')):
            with Astronomy(os.environ['DINCHARYA_PUBLIC_DE440S']) as astronomy:
                engine=RecurrenceResearch(astronomy)
                a=engine.preview(self.rule,date(2023,8,23),date(2023,8,28))
                b=engine.preview(self.rule,date(2023,8,24),date(2023,8,27))
                p=self.submit(a)[0];self.approve(p);self.c.materialize(p.proposal_id)
                self.assertEqual(self.submit(b)[0],p)
                self.c.materialize(p.proposal_id)
        self.assertEqual(len(self.c.entries()),1)

    def test_forged_selected_day_outside_physical_interval_rejected(self):
        preview=deepcopy(self.preview);row=preview['occurrences'][0]
        row['selected_date']='2030-01-01';row['sunrise_dates']=['2030-01-01']
        with self.assertRaises(ContractDenied):self.submit(preview)
        self.assertEqual(self.c.entries(),())

    def test_valid_first_row_invalid_second_row_leaves_no_partial_proposals(self):
        preview=deepcopy(self.fixtures['both'])
        preview['occurrences'][1]['selected_date']=None
        with self.assertRaises(ContractDenied):self.submit(preview,replace(self.rule,intercalation='both'))
        self.assertEqual(self.c._proposals,{})
        self.assertEqual(self.c._generations,{})
