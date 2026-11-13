"""Offline controlled validation. Exit 2: unresolved evidence, never scheduling."""
import argparse
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import resource
import sys
import time
from .feasibility import deny_network


def experiment(kernel):
    from .astronomy import Astronomy
    from .investigation import ControlledAstronomy, LahiriHypothesis, PROFILE
    import erfa
    base=Path(__file__).parent
    raw=(base/'references.json').read_bytes()
    refs=json.loads(raw)
    research=json.loads((base/'research-references.json').read_text())
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=research['baseline_reference_sha256']:
        raise ValueError('Established references changed')
    wall,cpu=time.perf_counter(),time.process_time()

    def compare(a,ref):
        at=datetime.fromisoformat(ref['at'])
        rows=[r for r in a.transitions(at-timedelta(hours=1),at+timedelta(hours=1))
              if r['ordinal']==ref['ordinal']]
        if len(rows)!=1: raise ValueError('Nonunique reference crossing')
        delta=(datetime.fromisoformat(rows[0]['at'])-at).total_seconds()
        return dict(reference=ref,calculated_at=rows[0]['at'],delta_seconds=delta,
                    within_numeric_threshold=abs(delta)<=ref['tolerance_seconds'])

    modes=[]
    for position in ('apparent','astrometric','geometric'):
        for frame in ('true_date','mean_date','J2000'):
            with ControlledAstronomy(kernel,position,frame) as a:
                modes.append(dict(position=position,frame=frame,
                                  comparisons=[compare(a,r) for r in refs['transitions']]))
    with Astronomy(kernel) as a:
        h=LahiriHypothesis(a)
        control=LahiriHypothesis(a,0)
        epochs=[]
        for r in research['epoch_checks']:
            at=datetime.fromisoformat(r['at'])
            delta=(h.ayanamsa_at(at)-r['degrees'])*3600
            epochs.append(dict(reference=r,delta_arcsec=delta,
                uncorrected_anchor_delta_arcsec=(control.ayanamsa_at(at)-r['degrees'])*3600,
                within_numeric_threshold=abs(delta)<=r['tolerance_arcsec']))
        solar=[]
        for r in research['solar_ingresses']:
            at=datetime.fromisoformat(r['at'])
            rows=[x for x in h.solar_ingresses(at-timedelta(days=1),at+timedelta(days=1)) if x['sign']==r['sign']]
            if len(rows)!=1: raise ValueError('Nonunique solar crossing')
            delta=(datetime.fromisoformat(rows[0]['at'])-at).total_seconds()
            solar.append(dict(reference=r,calculated_at=rows[0]['at'],delta_seconds=delta,
                              within_numeric_threshold=abs(delta)<=r['tolerance_seconds']))
        months=[]
        for r in research['amanta_cases']:
            actual=h.amanta_diagnostic(datetime.fromisoformat(r['at']))
            months.append(dict(reference=r,actual=actual,
                matches_selected_reference=(actual['candidate_amanta_month']==r['month'] and
                    actual['candidate_intercalation']==r['intercalation'])))
        result=dict(status='validation_incomplete_not_for_scheduling',usable_for_scheduling=False,
            baseline_reference_sha256=digest,ephemeris_sha256=a.metadata['sha256'],
            dependencies=a.metadata['dependencies'],erfa_version=erfa.version.erfa_version,
            sofa_version=erfa.version.sofa_version,profile=PROFILE,
            controlled_conventions=modes,
            additional_transitions=[compare(a,r) for r in research['additional_transitions']],
            lahiri_epoch_checks=epochs,solar_ingresses=solar,selected_amanta_cases=months,
            limitations=['Drik differences unexplained; original 60-second gate failed',
                'Himalayan parsed evidence provisional; numerical lineage unknown',
                'Epoch table vendor reproduction, not independent PAC epoch validation',
                'Selected 2023 ingress/Amanta agreement is not general month validation',
                'Purnimanta naming, Kshaya and annual APIs remain unsupported',
                'Sunrise model and long-range timing accuracy not independently validated'])
    result['metrics']=dict(wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu,
                          peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ephemeris',required=True,type=Path)
    args=parser.parse_args()
    sys.addaudithook(deny_network)
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    try: result=experiment(args.ephemeris)
    except Exception:
        print('Validation unavailable; no fallback or scheduling result',file=sys.stderr)
        return 1
    print(json.dumps(result,indent=2,sort_keys=True))
    return 2


if __name__=='__main__':
    raise SystemExit(main())
