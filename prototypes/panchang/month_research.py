"""Evidence-bounded lunar-month research; never a scheduling API."""
from datetime import date, datetime, timedelta
import json
from pathlib import Path

from .astronomy import Unsupported, aware
from .investigation import LahiriHypothesis, PROFILE

MONTH_PROFILE=PROFILE+'/paksha-conversion-v1'
FIXTURES=Path(__file__).with_name('month-references.json')


class MonthResearch:
    def __init__(self,astronomy):
        self.a=astronomy
        self.h=LahiriHypothesis(astronomy)

    def candidate(self,instant,convention='purnimanta'):
        instant=aware(instant)
        if convention not in ('amanta','purnimanta'):
            raise Unsupported('Unsupported month research convention')
        tithi=self.a.tithi_interval(instant)
        current=self.h.amanta_diagnostic(instant)
        name=current['candidate_amanta_month']
        intercalation=current['candidate_intercalation']
        rule='same_amanta_lunation'
        if convention=='purnimanta' and tithi['paksha']=='krishna' and intercalation=='ordinary':
            following=self.h.amanta_diagnostic(datetime.fromisoformat(current['end'])+timedelta(days=2))
            name=following['candidate_amanta_month']
            # Before an adhika lunation this is the ORDINARY Krishna half.
            # Adhika itself retains its name/flag for both pakshas.
            rule='ordinary_krishna_uses_following_amanta_name'
        elif convention=='purnimanta' and intercalation=='adhika':
            rule='adhika_retains_amanta_name_and_paksha'
        return dict(month=name,intercalation=intercalation,convention=convention,
                    ordinal=tithi['ordinal'],paksha=tithi['paksha'],
                    amanta_start=current['start'],amanta_end=current['end'],
                    conversion_rule=rule,profile=MONTH_PROFILE,
                    status='candidate_not_general_validation',usable_for_scheduling=False)

    def chaitra_anchor_year(self,instant):
        """Research cycle token, NOT a Vikrama/Shaka/regional era conversion."""
        instant=aware(instant)
        probe=instant
        for _ in range(15):
            current=self.h.amanta_diagnostic(probe)
            start=datetime.fromisoformat(current['start'])
            if current['candidate_amanta_month']=='chaitra' and current['candidate_intercalation']=='ordinary':
                return start.year
            # Skip guarded numerical endpoints; inspect previous lunation interior.
            probe=start-timedelta(days=2)
        raise Unsupported('No unambiguous ordinary Chaitra anchor')

    def annual_example(self,year,month,ordinal,intercalation,convention='purnimanta'):
        """Only explicit source-backed rule/year examples, not a general annual API.

        year is the Gregorian search year, not an era year. No private birth data.
        Both ordinary/adhika must be explicit; no inferred anniversary policy.
        """
        if (type(year) is not int or type(ordinal) is not int or not 1<=ordinal<=30
                or not isinstance(month,str) or intercalation not in ('ordinary','adhika')
                or convention not in ('amanta','purnimanta')):
            raise Unsupported('Unsupported experimental annual rule')
        refs=json.loads(FIXTURES.read_text())
        matching=[r for r in refs['annual_examples'] if
                  (r['year'],r['month'],r['ordinal'],r['intercalation'],r['convention'])==
                  (year,month,ordinal,intercalation,convention)]
        if len(matching)!=1:
            raise Unsupported('Annual rule/year has no reviewed evidence fixture')
        ref=matching[0]
        start,end=[date.fromisoformat(x) for x in ref['window']]
        # Calculate, then compare; never return the fixture's date as calculation.
        rows=self.a.monthly_preview(ordinal,start,end)
        found=[]
        for row in rows:
            a,b=[datetime.fromisoformat(row[k]) for k in ('start','end')]
            label=self.candidate(a+(b-a)/2,convention)
            if (label['month'],label['intercalation'])==(month,intercalation):
                found.append((row,label))
        if len(found)!=1:
            raise Unsupported('Evidence example occurrence is ambiguous or unavailable')
        row,label=found[0]
        if row['selected_date']!=ref['selected_date'] or row['sunrise_dates']!=ref['sunrise_dates']:
            raise Unsupported('Calculated occurrence disagrees with evidence fixture')
        result=dict(row)
        result.update(month=month,intercalation=intercalation,convention=convention,
                    gregorian_search_year=year,chaitra_anchor_year=self.chaitra_anchor_year(
                        datetime.fromisoformat(row['start'])+timedelta(hours=1)),
                    research_identity=f'{MONTH_PROFILE}/{convention}/{year}/{month}/{intercalation}/{ordinal}',
                    evidence_id=ref['id'],status='needs_review' if row['selected_date'] is None
                    else 'evidence_bounded_experimental_preview',usable_for_scheduling=False)
        return result
