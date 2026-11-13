"""General offline PERSONAL lunar previews. No scheduling or reference-table lookup."""
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from datetime import date,datetime,timedelta
import hashlib
import json

from .astronomy import DELHI,UTC,Unsupported,aware,iso,MODELS
from .investigation import LahiriHypothesis,PROFILE

MONTHS=('chaitra','vaishakha','jyeshtha','ashadha','shravana','bhadrapada',
        'ashvina','kartika','margashirsha','pausha','magha','phalguna')
# Selected agreement in accepted research, NOT general month certification.
RESEARCH_NAMES=frozenset(('chaitra','vaishakha','ashadha','shravana','pausha','magha','phalguna'))
VERSION='personal-lunar-preview-v1'
DATE_GUARD_SECONDS=300  # Separate conservative date gate, not a timing tolerance.


@dataclass(frozen=True)
class LunarRule:
    paksha: str
    tithi: int
    intercalation: str
    convention: str='purnimanta'
    month: str|None=None
    repeated: str='review'
    birth_basis: str='explicit_rule'

    def __post_init__(self):
        if (self.paksha not in ('shukla','krishna') or type(self.tithi) is not int
                or not 1<=self.tithi<=15 or self.intercalation not in ('ordinary','adhika','both')
                or self.convention not in ('amanta','purnimanta')
                or self.month is not None and self.month not in MONTHS
                or self.repeated not in ('review','first','last')
                or self.birth_basis not in ('explicit_rule','instant','sunrise')):
            raise Unsupported('Unsupported personal lunar rule')

    @property
    def ordinal(self): return self.tithi+(15 if self.paksha=='krishna' else 0)


class RecurrenceResearch:
    """Single-process, single-thread research evaluator; injected astronomy is owned.

    Fixed profile; month LRU <=32, preview LRU <=8, astronomy sunrise cache <=800.
    No reference fixture or private birth record is read/stored in a cache.
    """
    def __init__(self,astronomy,sunrise_model='upper_limb_50'):
        if not isinstance(sunrise_model,str) or sunrise_model not in MODELS:
            raise Unsupported('Unreviewed sunrise profile')
        self.a=astronomy
        self.h=LahiriHypothesis(astronomy)
        self.sunrise_model=sunrise_model
        self._profile=self._fingerprint()
        self.profile=VERSION+'/'+self._profile
        self._months=OrderedDict()
        self._previews=OrderedDict()
        self.month_misses=0
        self.preview_hits=0

    def _fingerprint(self):
        values=dict(version=VERSION,lahiri=PROFILE,metadata=self.a.metadata,
                    latitude=self.a.latitude,longitude=self.a.longitude,elevation_m=0,
                    timezone='Asia/Kolkata',sunrise_model=self.sunrise_model,
                    numerical_guard_seconds=.1,date_guard_seconds=DATE_GUARD_SECONDS,
                    month_names=sorted(RESEARCH_NAMES),conversion='skip-adhika-for-ordinary-krishna-v1')
        return hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def _check(self):
        if self._fingerprint()!=self._profile or self.profile!=VERSION+'/'+self._profile:
            self.clear()
            raise Unsupported('Calculation profile changed; create a fresh evaluator')

    def clear(self):
        self._months.clear();self._previews.clear();self.a._sunrises.clear()

    def _month(self,instant):
        instant=aware(instant)
        for key,(start,end,result) in list(self._months.items()):
            if start+timedelta(seconds=DATE_GUARD_SECONDS)<instant<end-timedelta(seconds=DATE_GUARD_SECONDS):
                self._months.move_to_end(key)
                return result
        result=self.h.amanta_diagnostic(instant)
        start,end=[datetime.fromisoformat(result[k]) for k in ('start','end')]
        if min((instant-start).total_seconds(),(end-instant).total_seconds())<=DATE_GUARD_SECONDS:
            raise Unsupported('Lunar month boundary requires review')
        self.month_misses+=1
        # Date-based cache key only for lookup; containment remains exact and guarded.
        self._months[start.date().isoformat()]=(start,end,result)
        while len(self._months)>32:self._months.popitem(last=False)
        return result

    def _label(self,instant,ordinal,convention):
        current=self._month(instant)
        canonical=current
        flag=current['candidate_intercalation']
        supported=current['candidate_amanta_month'] in RESEARCH_NAMES
        if convention=='purnimanta' and ordinal>15 and flag=='ordinary':
            following=self._month(datetime.fromisoformat(current['end'])+timedelta(days=2))
            supported &= following['candidate_amanta_month'] in RESEARCH_NAMES
            canonical=following
            if following['candidate_intercalation']=='adhika':
                canonical=self._month(datetime.fromisoformat(following['end'])+timedelta(days=2))
                if (canonical['candidate_intercalation']!='ordinary' or
                        canonical['candidate_amanta_month']!=following['candidate_amanta_month']):
                    raise Unsupported('Exceptional adjacent month conversion requires review')
        start=datetime.fromisoformat(canonical['start'])
        # A date discriminator must not flip due to solver rounding at UTC midnight.
        midnight=datetime.combine(start.date(),datetime.min.time(),UTC)
        if min((start-midnight).total_seconds(),(midnight+timedelta(days=1)-start).total_seconds())<=DATE_GUARD_SECONDS:
            raise Unsupported('Month anchor date is numerically sensitive')
        return dict(month=canonical['candidate_amanta_month'],intercalation=flag,
                    month_anchor=start.date().isoformat(),supported=bool(supported and
                        canonical['candidate_amanta_month'] in RESEARCH_NAMES))

    def _dawn(self,day):
        result=self.a.sunrise(day,self.sunrise_model)
        while len(self.a._sunrises)>800:self.a._sunrises.pop(next(iter(self.a._sunrises)))
        return result

    def from_birth(self,instant,*,basis,convention='purnimanta',repeated='review'):
        """Explicit birth interpretation; future date assignment remains at sunrise."""
        self._check()
        instant=aware(instant)
        if basis not in ('instant','sunrise'):
            raise Unsupported('Choose instant or sunrise birth interpretation explicitly')
        observation=instant if basis=='instant' else self._dawn(instant.astimezone(DELHI).date())
        interval=self.a.tithi_interval(observation)
        if min((observation-datetime.fromisoformat(interval['start'])).total_seconds(),
               (datetime.fromisoformat(interval['end'])-observation).total_seconds())<=DATE_GUARD_SECONDS:
            raise Unsupported('Birth interpretation is near an uncertain boundary')
        label=self._label(observation,interval['ordinal'],convention)
        if not label['supported']:raise Unsupported('Birth month case has insufficient research support')
        return LunarRule(interval['paksha'],interval['paksha_day'],label['intercalation'],
                         convention,label['month'],repeated,basis)

    def annual(self,rule,year):
        """Enumerate a full Gregorian civil search year, not an era-year formula."""
        if not isinstance(rule,LunarRule) or rule.month is None or type(year) is not int or not 1900<=year<=2100:
            raise Unsupported('Annual research requires a named rule and supported search year')
        return self.preview(rule,date(year,1,1),date(year+1,1,1))

    def monthly(self,rule,start,end):
        if not isinstance(rule,LunarRule) or rule.month is not None:
            raise Unsupported('Monthly research requires a rule without a fixed month')
        return self.preview(rule,start,end)

    def preview(self,rule,start_day,end_day):
        self._check()
        if (not isinstance(rule,LunarRule) or type(start_day) is not date or type(end_day) is not date
                or not date(1900,1,1)<=start_day<end_day<=date(2101,1,1)
                or (end_day-start_day).days>366):
            raise Unsupported('Preview window must be supported, ordered and at most 366 civil days')
        key=(rule,start_day,end_day)
        if key in self._previews:
            self.preview_hits+=1;self._previews.move_to_end(key)
            return deepcopy(self._previews[key])
        start=datetime.combine(start_day,datetime.min.time(),DELHI).astimezone(UTC)
        end=datetime.combine(end_day,datetime.min.time(),DELHI).astimezone(UTC)
        roots=self.a._transitions(start-timedelta(days=2),end+timedelta(days=2))
        occurrences=[]
        for first,last in zip(roots,roots[1:]):
            if first['ordinal']!=rule.ordinal:continue
            a,b=[datetime.fromisoformat(r['at']) for r in (first,last)]
            if b<=start or a>=end:continue
            self.a._complete_bounds(a,b)
            dawns=[];uncertain=False
            day=a.astimezone(DELHI).date()
            while day<=b.astimezone(DELHI).date():
                if day>=date(2101,1,1):break
                dawn=self._dawn(day)
                uncertain |= min(abs((dawn-a).total_seconds()),abs((dawn-b).total_seconds()))<=120
                if a<=dawn<b:dawns.append(day.isoformat())
                day+=timedelta(days=1)
            try:
                label=self._label(a+(b-a)/2,rule.ordinal,rule.convention)
            except Unsupported:
                label=None
            if label is not None:
                if rule.month is not None and label['month']!=rule.month:continue
                if rule.intercalation!='both' and label['intercalation']!=rule.intercalation:continue
            reason='single_sunrise';chosen=None
            if label is None:reason='unsupported_month_calculation'
            elif not label['supported']:reason='unsupported_month_name'
            elif uncertain:reason='boundary_uncertainty'
            elif not dawns:reason='skipped_at_sunrise'
            elif len(dawns)>1 and rule.repeated=='review':reason='repeated_requires_policy'
            else:
                chosen=dawns[-1] if rule.repeated=='last' else dawns[0]
                if len(dawns)>1:reason='explicit_'+rule.repeated+'_of_repeated'
            # Never replace an out-of-window chosen day with another sunrise.
            if chosen is not None:
                if not start_day<=date.fromisoformat(chosen)<end_day:continue
            else:
                anchors=dawns or [a.astimezone(DELHI).date().isoformat()]
                if not any(start_day<=date.fromisoformat(d)<end_day for d in anchors):continue
            identity=None
            if label is not None and label['supported']:
                identity=dict(version=1,profile=self.profile,convention=rule.convention,
                              month=label['month'],intercalation=label['intercalation'],
                              month_anchor=label['month_anchor'],paksha=rule.paksha,tithi=rule.tithi)
            occurrences.append(dict(identity=identity,month=label['month'] if label else None,
                intercalation=label['intercalation'] if label else None,paksha=rule.paksha,tithi=rule.tithi,
                start=iso(a),end=iso(b),sunrise_dates=dawns,selected_date=chosen,reason=reason,
                status='experimental_date' if chosen else 'needs_review'))
        ids=[json.dumps(r['identity'],sort_keys=True) for r in occurrences if r['identity'] is not None]
        if len(ids)!=len(set(ids)):
            raise Unsupported('Duplicate lunar identity; no preview can be trusted')
        result=dict(profile=self.profile,occurrences=occurrences,
                    status='needs_review' if any(r['selected_date'] is None for r in occurrences) else 'experimental_preview',
                    birth_basis=rule.birth_basis,assignment='sunrise',calendar_date_gate='not_adopted',
                    validation_scope='selected_month_names_only_not_calendar_adoption',
                    usable_for_scheduling=False)
        self._previews[key]=deepcopy(result)
        while len(self._previews)>8:self._previews.popitem(last=False)
        return result
