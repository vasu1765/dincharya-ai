"""Offline all-name/identity/date-gate report. Exit2 is intentionally not adoption."""
import argparse
from datetime import datetime,date,timedelta
import hashlib,json,resource,sys,time
from pathlib import Path
from .feasibility import deny_network


def experiment(kernel):
    from .astronomy import Astronomy
    from .recurrence import RecurrenceResearch,LunarRule,reconcile_calculations
    path=Path(__file__).with_name('coverage-references.json')
    refs=json.loads(path.read_text())
    for name,digest in refs['accepted_sha256'].items():
        if hashlib.sha256(path.with_name(name).read_bytes()).hexdigest()!=digest:raise ValueError('Accepted fixture changed')
    wall=time.perf_counter()
    with Astronomy(kernel) as a:
        # Cold full-year performance measured before the evidence warms month caches.
        m=RecurrenceResearch(a);rule=LunarRule('shukla',9,'ordinary',month='chaitra')
        started=time.perf_counter();annual=m.annual(rule,2026);cold=time.perf_counter()-started
        misses=m.month_misses;started=time.perf_counter();warm=m.annual(rule,2026);warm_seconds=time.perf_counter()-started
        if warm!=annual or m.month_misses!=misses:raise ValueError('Cache mismatch')
        rows=[]
        for ref in refs['cases']:
            at=datetime.fromisoformat(ref['at']);ordinal=a.tithi_at(at)
            am=m._label(at,ordinal,'amanta');pu=m._label(at,ordinal,'purnimanta')
            rows.append(dict(reference=ref,amanta=am,purnimanta=pu,
                matches=(ordinal==ref['ordinal'] and am['month']==ref['amanta'] and
                         pu['month']==ref['purnimanta'] and am['supported'] and pu['supported'])))
        direct=[]
        for ref in refs['direct_purnimanta']:
            at=datetime.fromisoformat(ref['at']);actual=m._label(at,a.tithi_at(at),'purnimanta')
            direct.append(dict(reference=ref,actual=actual,matches=actual['month']==ref['purnimanta']))
        near=[];ref=refs['near_sunrise'];at=datetime.fromisoformat(ref['published_transition'])
        for horizon in ('upper_limb_50','pac_47_hypothesis'):
            dawn=a.sunrise(date.fromisoformat(ref['day']),horizon)
            margin=(at-dawn).total_seconds()
            near.append(dict(horizon=horizon,delhi_sunrise=dawn.isoformat(),
                delta_to_PAC_boundary_seconds=margin,ordinal=a.tithi_at(dawn),
                selected_date=RecurrenceResearch(a,horizon).preview(
                    LunarRule('krishna',7,'ordinary',convention='amanta',month='chaitra'),
                    date(2024,4,30),date(2024,5,2))['occurrences'][0]['selected_date'],
                matches=a.tithi_at(dawn)==ref['ending_ordinal'] and 300<margin<900))
        changed_profile=RecurrenceResearch(a,'pac_47_hypothesis').annual(rule,2026)
        reconciled=reconcile_calculations(annual,changed_profile)
        identity_stable=annual['occurrences'][0]['identity']==changed_profile['occurrences'][0]['identity']
        result=dict(status='all_name_research_checkpoint_not_adoption',usable_for_scheduling=False,
            base_commit='0a1cae678dc9a00a120a56a703f74a23935bfde2',fixture_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            cases=rows,direct_purnimanta=direct,near_sunrise=near,
            logical_identity_stable_across_profiles=identity_stable,
            identity_example=annual['occurrences'][0],reconciliation_same_date=reconciled,
            selected_calendar_checks_pass=all(r['matches'] for r in rows+direct+near),
            adoption_gate='incomplete_direct_reference_profile_exception_coverage_and_owner_approval',
            timing_diagnostics='Original60-second gates/fixtures unchanged; old failures retained, not rerun',
            metrics=dict(cold_annual_seconds=cold,warm_seconds=warm_seconds,
                historical_cold_annual_seconds=2.056093820996466,
                cold_ratio_to_previous=cold/2.056093820996466,month_cache_entries=len(m._months),
                preview_cache_entries=len(m._previews),total_wall_seconds=time.perf_counter()-wall,
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ephemeris',type=Path,required=True);args=p.parse_args()
    sys.addaudithook(deny_network)
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024));resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    try:r=experiment(args.ephemeris)
    except Exception:
        print('Coverage unavailable; no scheduling fallback',file=sys.stderr);return 1
    print(json.dumps(r,indent=2,sort_keys=True));return 2


if __name__=='__main__':raise SystemExit(main())
