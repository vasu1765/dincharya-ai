"""Synthetic, single-process proposal/approval/ledger contract. Never a scheduler.

No connection factory, transport, environment loading, filesystem or delivery API.
The caller supplies trusted validated research output and an in-process owner capability.
"""
from dataclasses import asdict,dataclass,field
from datetime import date,datetime
import hashlib,json
from uuid import UUID
from dincharya.reminders import DeliveryReceipt
from .astronomy import DELHI,Unsupported,aware
from .recurrence import LunarRule,logical_key,reconcile_calculations


class ContractDenied(ValueError): pass


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class Series:
    series_id: UUID
    kind: str

    def __post_init__(self):
        if not isinstance(self.series_id,UUID) or self.kind not in ('birthday','wedding_anniversary'):
            raise ContractDenied('Synthetic immutable personal series required')


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    series_id: UUID
    calendar_key: str
    rule_json: str
    selected_date: str
    profile: str
    series_generation: int
    observation: int
    requires_review: bool
    snapshot_json: str=field(repr=False)


@dataclass(frozen=True)
class Approval:
    action_id: UUID
    proposal_id: str
    snapshot_json: str=field(repr=False)


@dataclass(frozen=True)
class LedgerEntry:
    series_id: UUID
    calendar_key: str
    selected_date: str
    rule_json: str
    approval: Approval


@dataclass(frozen=True)
class FixtureHistory:
    fixture_id: UUID
    state: str
    receipt: DeliveryReceipt|None=field(default=None,repr=False)


class MemoryContract:
    """Isolated synthetic store. Not thread/process safe, durable or production auth.

    One owner capability is supplied by trusted test setup, never by actor-ID text.
    Candidate generations invalidate stale proposals; they do not edit approved rows.
    """
    def __init__(self,*,owner_capability):
        if owner_capability is None:raise ContractDenied('Trusted test owner capability required')
        self._owner=owner_capability
        self._series={};self._generations={};self._observations={}
        self._proposals={};self._approvals={};self._actions={};self._ledger={};self._history={}

    def _authorize(self,principal):
        if principal is not self._owner:raise ContractDenied('Unauthorized synthetic decision')

    def register(self,series):
        if not isinstance(series,Series):raise ContractDenied('Validated series required')
        previous=self._series.get(series.series_id)
        if previous is not None and previous!=series:raise ContractDenied('Series identity is immutable')
        if previous is None and len(self._series)>=16:raise ContractDenied('Synthetic capacity reached')
        self._series[series.series_id]=series
        return series

    def _validate(self,rule,preview):
        if not isinstance(rule,LunarRule) or rule.month is None:raise ContractDenied('Named personal rule required')
        try:
            # Reuse the exact research-only schema and duplicate identity checks.
            reconcile_calculations(preview,preview)
            if preview['birth_basis']!=rule.birth_basis or preview['assignment']!='sunrise':raise ValueError()
            if len(preview['occurrences'])>64:raise ValueError()
            result=[]
            for row in preview['occurrences']:
                identity=row['identity'];key=logical_key(identity)
                if (row['status']!='experimental_date' or row['selected_date'] is None
                        or row['reason'] not in ('single_sunrise','explicit_first_of_repeated','explicit_last_of_repeated')
                        or row['provenance']['profile']!=preview['profile']
                        or not isinstance(preview['profile'],str) or not preview['profile'].startswith('personal-lunar-preview-')
                        or row['selection_policy']!={'assignment':'sunrise','repeated':rule.repeated}):raise ValueError()
                if (identity['month'],identity['paksha'],identity['tithi'],identity['convention'])!=(rule.month,rule.paksha,rule.tithi,rule.convention):raise ValueError()
                if rule.intercalation!='both' and identity['intercalation']!=rule.intercalation:raise ValueError()
                if (row['month'],row['paksha'],row['tithi'],row['intercalation'])!=(identity['month'],identity['paksha'],identity['tithi'],identity['intercalation']):raise ValueError()
                dates=row['sunrise_dates']
                if not isinstance(dates,list) or not 1<=len(dates)<=2 or dates!=sorted(set(dates)):raise ValueError()
                for day in dates:
                    if type(day) is not str or date.fromisoformat(day).isoformat()!=day:raise ValueError()
                if len(dates)>1 and rule.repeated=='review':raise ValueError()
                expected=dates[-1] if rule.repeated=='last' else dates[0]
                if row['selected_date']!=expected:raise ValueError()
                start,end=[aware(datetime.fromisoformat(row[k])) for k in ('start','end')]
                if not 0<(end-start).total_seconds()<2*86400:raise ValueError()
                if any(not start.astimezone(DELHI).date()<=date.fromisoformat(day)<=end.astimezone(DELHI).date() for day in dates):raise ValueError()
                result.append((key,row))
            return result
        except (Unsupported,ValueError,TypeError,KeyError,OverflowError):
            raise ContractDenied('Preview is unsupported, unselected or inconsistent; nothing proposed') from None

    def submit(self,series_id,rule,preview):
        if series_id not in self._series:raise ContractDenied('Unknown synthetic series')
        rows=self._validate(rule,preview)  # Validate entire batch before changing any state.
        if not rows:return ()  # No-Adhika/no-match output is never a fallback proposal.
        rule_json=canonical(asdict(rule));rule_hash=digest(asdict(rule))
        old_rule,generation=self._generations.get(series_id,(None,0))
        changed_rule=old_rule is not None and old_rule!=rule_hash
        if old_rule!=rule_hash:generation+=1
        prepared=[]
        for key,row in rows:
            scoped=(series_id,key)
            signature=digest(dict(rule=rule_json,date=row['selected_date'],profile=preview['profile']))
            old_signature,observation=self._observations.get(scoped,(None,0))
            changed_observation=old_signature is not None and old_signature!=signature
            if old_signature!=signature:observation+=1
            pid=digest(dict(series=str(series_id),key=key,rule=rule_json,signature=signature,
                            generation=generation,observation=observation))
            if pid in self._proposals:
                prepared.append((scoped,signature,observation,self._proposals[pid]));continue
            existing=self._ledger.get(scoped)
            review=changed_rule or changed_observation or existing is not None and (
                existing.selected_date!=row['selected_date'] or existing.rule_json!=rule_json)
            snapshot=canonical(dict(series=asdict(self._series[series_id])|{'series_id':str(series_id)},
                identity=row['identity'],rule=asdict(rule),date=row['selected_date'],profile=preview['profile'],
                series_generation=generation,observation=observation,evidence=row))
            proposal=Proposal(pid,series_id,key,rule_json,row['selected_date'],preview['profile'],
                              generation,observation,bool(review),snapshot)
            prepared.append((scoped,signature,observation,proposal))
        if len(self._proposals)+sum(p.proposal_id not in self._proposals for _,_,_,p in prepared)>1024:
            raise ContractDenied('Synthetic capacity reached')
        self._generations[series_id]=(rule_hash,generation)
        for scoped,signature,observation,proposal in prepared:
            self._observations[scoped]=(signature,observation)
            self._proposals.setdefault(proposal.proposal_id,proposal)
        return tuple(p for _,_,_,p in prepared)

    def _fresh(self,proposal):
        if (self._generations[proposal.series_id][1]!=proposal.series_generation
                or self._observations[(proposal.series_id,proposal.calendar_key)][1]!=proposal.observation):
            raise ContractDenied('Stale snapshot; submit and approve a fresh proposal')

    def approve(self,proposal_id,*,principal,action_id,acknowledge_changes=False):
        self._authorize(principal)
        if not isinstance(action_id,UUID) or type(acknowledge_changes) is not bool:raise ContractDenied('Decision action ID and explicit boolean acknowledgement required')
        if proposal_id not in self._proposals:raise ContractDenied('Unknown proposal')
        proposal=self._proposals[proposal_id]
        command=(proposal_id,acknowledge_changes)
        if action_id in self._actions:
            previous,approval=self._actions[action_id]
            if command!=previous:raise ContractDenied('Action ID cannot approve a different command')
            return approval  # Replay never restores freshness or materializes anything.
        self._fresh(proposal)
        if proposal.requires_review and acknowledge_changes is not True:raise ContractDenied('Changed snapshot requires explicit review acknowledgement')
        if proposal_id in self._approvals:raise ContractDenied('Proposal already decided; replay original action')
        approval=Approval(action_id,proposal_id,proposal.snapshot_json)
        self._approvals[proposal_id]=approval;self._actions[action_id]=(command,approval)
        return approval

    def materialize(self,proposal_id):
        if proposal_id not in self._approvals:raise ContractDenied('Explicit occurrence approval required')
        proposal=self._proposals[proposal_id];self._fresh(proposal)
        key=(proposal.series_id,proposal.calendar_key);existing=self._ledger.get(key)
        if existing is not None:
            if (existing.selected_date,existing.rule_json)!=(proposal.selected_date,proposal.rule_json):
                raise ContractDenied('Existing approved occurrence is immutable; replacement requires separate review')
            return existing  # Preserve original approval/provenance/history, even after recalculation.
        entry=LedgerEntry(proposal.series_id,proposal.calendar_key,proposal.selected_date,proposal.rule_json,self._approvals[proposal_id])
        self._ledger[key]=entry
        return entry

    def seed_history_for_test(self,series_id,calendar_key,history,*,principal):
        self._authorize(principal)
        key=(series_id,calendar_key)
        if (key not in self._ledger or not isinstance(history,FixtureHistory)
                or not isinstance(history.fixture_id,UUID) or history.state not in ('sent','uncertain')
                or history.state=='sent' and not isinstance(history.receipt,DeliveryReceipt)
                or history.state=='uncertain' and history.receipt is not None):
            raise ContractDenied('Invented terminal history fixture requires an approved synthetic entry')
        previous=self._history.get(key)
        if previous is not None and previous!=history:raise ContractDenied('Terminal fixture history is immutable')
        self._history[key]=history
        return history

    def entries(self):return tuple(self._ledger.values())
    def histories(self):return tuple(self._history.items())
    def approvals(self):return tuple(self._approvals.values())
