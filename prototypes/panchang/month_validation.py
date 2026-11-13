"""Offline, selected lunar-month evidence checks. Exit 2: no engine adoption."""
import argparse
from datetime import datetime,timedelta
import hashlib
import json
from pathlib import Path
import resource
import sys
import time
from .feasibility import deny_network


def experiment(kernel):
    from .astronomy import Astronomy
    from .month_research import MonthResearch,FIXTURES,MONTH_PROFILE
    refs=json.loads(FIXTURES.read_text())
    for name,digest in refs['accepted_fixture_sha256'].items():
        if hashlib.sha256(FIXTURES.with_name(name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Accepted research evidence changed')
    wall,cpu=time.perf_counter(),time.process_time()
    with Astronomy(kernel) as a:
        model=MonthResearch(a)
        cases=[]
        for ref in refs['cases']:
            for conv in ('amanta','purnimanta'):
                if ref[conv] is None: continue
                actual=model.candidate(datetime.fromisoformat(ref['at']),conv)
                cases.append(dict(reference_id=ref['id'],actual=actual,
                    matches_reference=(actual['month']==ref[conv] and
                    actual['intercalation']==ref['intercalation'] and actual['ordinal']==ref['ordinal'])))
        comparisons=[]
        for ref in refs['transitions']:
            at=datetime.fromisoformat(ref['at'])
            rows=[r for r in a.transitions(at-timedelta(hours=1),at+timedelta(hours=1)) if r['ordinal']==ref['ordinal']]
            if len(rows)!=1: raise ValueError('Nonunique public transition fixture')
            delta=(datetime.fromisoformat(rows[0]['at'])-at).total_seconds()
            comparisons.append(dict(reference=ref,calculated_at=rows[0]['at'],delta_seconds=delta,
                                    within_numeric_threshold=abs(delta)<=ref['tolerance_seconds']))
        examples=[]
        for ref in refs['annual_examples']:
            actual=model.annual_example(ref['year'],ref['month'],ref['ordinal'],ref['intercalation'],ref['convention'])
            examples.append(actual)
        anchors=[]
        for ref in refs['chaitra_anchor_cases']:
            actual=model.chaitra_anchor_year(datetime.fromisoformat(ref['at']))
            anchors.append(dict(reference=ref,actual=actual,matches_reference=actual==ref['expected_year']))
        result=dict(status='selected_month_research_not_general_validation',usable_for_scheduling=False,
            latest_pushed_base='452bbcd28653ae8a8530ada57c3e0bd33e2f2d6b',profile=MONTH_PROFILE,
            fixture_sha256=hashlib.sha256(FIXTURES.read_bytes()).hexdigest(),
            dependencies=a.metadata['dependencies'],ephemeris_sha256=a.metadata['sha256'],
            month_cases=cases,new_transition_comparisons=comparisons,annual_examples=examples,
            year_anchor_checks=anchors,limitations=refs['limitations'])
    result['metrics']=dict(wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu,
                          peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ephemeris',type=Path,required=True)
    args=parser.parse_args()
    sys.addaudithook(deny_network)
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    try: result=experiment(args.ephemeris)
    except Exception:
        print('Month research unavailable; no guessed preview or fallback',file=sys.stderr)
        return 1
    print(json.dumps(result,indent=2,sort_keys=True))
    return 2


if __name__=='__main__': raise SystemExit(main())
