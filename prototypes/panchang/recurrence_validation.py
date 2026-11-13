"""Offline personal-preview and calendar-date checkpoint. Exit 2: not adoption."""
import argparse
from datetime import date,datetime,timedelta
import hashlib
import json
from pathlib import Path
import resource
import sys
import time
from .feasibility import deny_network


def experiment(kernel):
    from .astronomy import Astronomy
    from .recurrence import RecurrenceResearch,LunarRule,DATE_GUARD_SECONDS
    path=Path(__file__).with_name('calendar-references.json')
    refs=json.loads(path.read_text())
    for name,digest in refs['accepted_sha256'].items():
        if hashlib.sha256(path.with_name(name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Accepted evidence changed')
    wall=time.perf_counter()
    with Astronomy(kernel) as a:
        model=RecurrenceResearch(a)
        days=[]
        for ref in refs['calendar_days']:
            hypotheses=[]
            for name in ('upper_limb_50','pac_47_hypothesis'):
                actual=a.at_sunrise(date.fromisoformat(ref['day']),name)
                dawn=datetime.fromisoformat(actual['sunrise'])
                gap=min((dawn-datetime.fromisoformat(actual['start'])).total_seconds(),
                        (datetime.fromisoformat(actual['end'])-dawn).total_seconds())
                hypotheses.append(dict(model=name,sunrise=actual['sunrise'],ordinal=actual['ordinal'],
                                       boundary_distance_seconds=gap,
                                       matches=actual['ordinal']==ref['ordinal'] and gap>DATE_GUARD_SECONDS))
            days.append(dict(reference=ref,hypotheses=hypotheses))
        selection=[]
        for ref in refs['selection_cases']:
            for policy in ('review','first','last'):
                rule=LunarRule(ref['paksha'],ref['tithi'],ref['intercalation'],month=ref['month'],repeated=policy)
                row=model.preview(rule,*[date.fromisoformat(x) for x in ref['window']])['occurrences'][0]
                selection.append(dict(reference_id=ref['id'],policy=policy,actual=row,
                    matches=(row['sunrise_dates']==ref['sunrise_dates'] and
                        row['selected_date']==(None if policy=='review' else ref[policy]))))
        rule=LunarRule('shukla',9,'ordinary',month='chaitra')
        cold=time.perf_counter();annual=model.annual(rule,2026);cold=time.perf_counter()-cold
        misses=model.month_misses
        warm=time.perf_counter();cached=model.annual(rule,2026);warm=time.perf_counter()-warm
        if annual!=cached or model.month_misses!=misses:raise ValueError('Cache altered results or recalculated months')
        monthly=model.monthly(LunarRule('shukla',3,'both'),date(2024,1,1),date(2025,1,1))
        pairs=[]
        for paksha,flag in [('krishna','ordinary'),('shukla','ordinary'),('krishna','adhika'),('shukla','adhika')]:
            pairs.append(model.annual(LunarRule(paksha,1,flag,month='shravana'),2023))
        timing=[]
        for ref in refs['timing_diagnostics']:
            at=datetime.fromisoformat(ref['at'])
            rows=[r for r in a.transitions(at-timedelta(hours=1),at+timedelta(hours=1)) if r['ordinal']==ref['ordinal']]
            if len(rows)!=1:raise ValueError('Nonunique timing crossing')
            delta=(datetime.fromisoformat(rows[0]['at'])-at).total_seconds()
            timing.append(dict(reference=ref,calculated_at=rows[0]['at'],delta_seconds=delta,
                               within_original_sixty_second_gate=abs(delta)<=60))
        result=dict(status='research_checkpoint_not_scheduling',usable_for_scheduling=False,
            base_commit='2bd37c09c4a3e25d4dcc3d6e7476c0665ac46b77',profile=model.profile,
            fixture_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),calendar_days=days,
            selected_calendar_date_gate=all(h['matches'] for d in days for h in d['hypotheses']) and
                                        all(s['matches'] for s in selection),
            calendar_adoption_gate='incomplete_profile_and_coverage_not_owner_approved',
            selection_cases=selection,arbitrary_annual=annual,arbitrary_monthly=monthly,
            purnimanta_adhika_pairs=pairs,new_timing_diagnostics=timing,
            existing_timing_gate='still_failed_original_fixtures_unchanged',
            metrics=dict(cold_annual_seconds=cold,warm_identical_seconds=warm,month_cache_entries=len(model._months),
                         preview_cache_entries=len(model._previews),warm_new_month_calculations=0,
                         total_wall_seconds=time.perf_counter()-wall,
                         peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ephemeris',type=Path,required=True)
    args=parser.parse_args()
    sys.addaudithook(deny_network)
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    try:result=experiment(args.ephemeris)
    except Exception:
        print('Personal lunar preview unavailable; no fallback',file=sys.stderr)
        return 1
    print(json.dumps(result,indent=2,sort_keys=True))
    return 2


if __name__=='__main__':raise SystemExit(main())
