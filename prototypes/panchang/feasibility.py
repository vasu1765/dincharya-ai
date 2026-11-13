"""Reproducible public-reference experiment. Exit 2 means feasibility incomplete."""
import argparse
from datetime import date, datetime, timedelta
import json
import platform
import resource
import sys
import time
from pathlib import Path


def deny_network(event, args):
    if event in ('socket.connect','socket.getaddrinfo','socket.bind'):
        raise RuntimeError('Network disabled during offline feasibility execution')


def experiment(ephemeris):
    from prototypes.panchang.astronomy import Astronomy, UTC, iso
    references=json.loads(Path(__file__).with_name('references.json').read_text())
    wall,cpu=time.perf_counter(),time.process_time()
    with Astronomy(ephemeris) as a:
        loaded=time.perf_counter()
        comparisons=[]
        for ref in references['transitions']:
            at=datetime.fromisoformat(ref['at']).astimezone(UTC)
            candidates=[r for r in a.transitions(at-timedelta(hours=1),at+timedelta(hours=1))
                        if r['ordinal']==ref['ordinal']]
            if len(candidates)!=1:
                raise ValueError('Reference transition not uniquely bracketed')
            row=candidates[0]
            delta=(datetime.fromisoformat(row['at'])-at).total_seconds()
            comparisons.append(dict(source=ref['source'],published_at=ref['at'],calculated_at=row['at'],
                ordinal=ref['ordinal'],delta_seconds=delta,tolerance_seconds=ref['tolerance_seconds'],
                within_numeric_threshold=abs(delta)<=ref['tolerance_seconds']))
        sunrise=a.at_sunrise(date(2026,1,14))
        sunrise['reference_delta_seconds']=(datetime.fromisoformat(sunrise['sunrise'])-
            datetime.fromisoformat(references['sunrise']['at'])).total_seconds()
        sunrise['matching_reference_metadata_validated']=False
        sunrise['pac47_sunrise']=iso(a.sunrise(date(2026,1,14),'pac_47_hypothesis'))
        annual_started=time.perf_counter()
        yearly=a.transitions(datetime(2026,1,1,tzinfo=UTC),datetime(2027,1,1,tzinfo=UTC))
        annual_seconds=time.perf_counter()-annual_started
        repeated=a.monthly_preview(9,date(2026,11,1),date(2026,12,1))
        skipped=a.monthly_preview(11,date(2026,11,1),date(2026,12,1))
        diagnostics=a.lunation_diagnostics(datetime(2023,7,25,tzinfo=UTC))
        ordinary=a.lunation_diagnostics(datetime(2023,8,25,tzinfo=UTC))
        month_bounds={c:a.month_boundaries(datetime(2023,7,25,tzinfo=UTC),c)
                      for c in ('purnimanta','amanta')}
        result=dict(status='feasibility_incomplete_not_for_scheduling',usable_for_scheduling=False,
            engine='Skyfield',dependencies=a.metadata['dependencies'],python=platform.python_version(),
            platform=platform.system()+' '+platform.machine(),ephemeris_sha256=a.metadata['sha256'],
            skyfield_data_sha256=a.metadata['skyfield_data_sha256'],
            timezone_tzif_sha256=a.metadata['timezone_tzif_sha256'],
            profile=dict(latitude=a.latitude,longitude=a.longitude,elevation_m=0,
                         timezone='Asia/Kolkata',default_month_convention='purnimanta',
                         coordinates='WGS84',sunrise_model='upper_limb_50',
                         longitudes='geocentric apparent true ecliptic/equinox of date'),
            comparisons=comparisons,sunrise=sunrise,month_boundaries=month_bounds,
            known_intercalary_sensitivity=diagnostics,ordinary_lunation_sensitivity=ordinary,
            repeated_tithi=repeated,skipped_tithi=skipped,
            unsupported=['validated Lahiri ayanamsa','named lunar months and exceptional Purnimanta conversion',
                'general validated Adhika/Kshaya detection','annual lunar birthday/anniversary dates',
                'festival rules','persistent schedules or delivery'],
            metrics=dict(kernel_and_data_load_seconds=loaded-wall,year_transition_seconds=annual_seconds,
                year_transition_count=len(yearly),max_transition_bracket_seconds=max(r['bracket_seconds'] for r in yearly)))
    result['metrics'].update(total_wall_seconds=time.perf_counter()-wall,
        total_cpu_seconds=time.process_time()-cpu,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ephemeris',type=Path,required=True)
    args=parser.parse_args()
    sys.addaudithook(deny_network)
    # Limit this isolated process, not any running application. Linux target.
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    try:
        result=experiment(args.ephemeris)
    except Exception:
        print('Feasibility unavailable; no fallback or scheduling result',file=sys.stderr)
        return 1
    print(json.dumps(result,indent=2,sort_keys=True))
    return 2


if __name__=='__main__':
    raise SystemExit(main())
