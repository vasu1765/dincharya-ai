"""One-shot historical calculation in the accepted, isolated astronomy dependency scope."""
from pathlib import Path
from subprocess import TimeoutExpired
import subprocess
import sys
import sysconfig
import json


def child(command, **options):
    try:
        return subprocess.run(command,**options)
    except TimeoutExpired:
        raise TimeoutError("Calendar calculation timed out") from None


def lookup(question,detailed,kernel,wheel,*,structured=False):
    from dincharya.attended_runtime import verify_wheel
    verify_wheel(wheel)
    if len(question)>160:
        return {"text":"Please give one Delhi date and optional local time.","context":None} if structured else "Please give one Delhi date and optional local time."
    r=child([sys.executable,"-I","-S","-B",str(Path(__file__).resolve()),str(wheel),
                      str(kernel),("structured-" if structured else "")+("detail" if detailed else "brief")],input=question,text=True,
                     env={"TZ":"UTC","OPENBLAS_NUM_THREADS":"1"},cwd="/",timeout=30,capture_output=True,close_fds=True)
    if r.returncode or not 0<len(r.stdout)<=4096:
        raise RuntimeError("Historical calculation unavailable")
    return json.loads(r.stdout) if structured else r.stdout


def anniversary(rule,year,kernel,wheel):
    from dincharya.attended_runtime import verify_wheel
    verify_wheel(wheel)
    result=child([sys.executable,"-I","-S","-B",str(Path(__file__).resolve()),str(wheel),str(kernel),
                           "guarded-anniversary"],input=json.dumps(dict(rule=rule,year=year)),text=True,
                          env={"TZ":"UTC","OPENBLAS_NUM_THREADS":"1"},cwd="/",timeout=45,capture_output=True,close_fds=True)
    if result.returncode or not 0<len(result.stdout)<=4096:
        raise RuntimeError("Lunar calculation unavailable")
    return json.loads(result.stdout)


if __name__=="__main__":
    wheel,kernel,mode=sys.argv[1:]
    if not (sys.flags.isolated and sys.flags.no_site and Path(wheel).is_absolute() and Path(kernel).is_absolute()
            and mode in ("detail","brief","structured-detail","structured-brief","guarded-anniversary")):
        raise SystemExit(2)
    sys.path[:0]=[wheel,str(Path(__file__).resolve().parents[1])]
    sys.path.extend([sysconfig.get_path("purelib"),sysconfig.get_path("platlib")])
    from dincharya.daily_review import concise
    from dincharya.historical_panchang import HistoricalPanchang, historical_text, label
    from dincharya.lunar_intent import Clarify
    from prototypes.panchang.astronomy import Unsupported
    from prototypes.panchang.guarded import GuardedCalendar
    calendar=GuardedCalendar(Path(kernel))
    if mode=="guarded-anniversary":
        from dincharya.personal_lunar import candidate
        try:
            value=json.loads(sys.stdin.read(1025))
            result=candidate(calendar,value["rule"],value["year"])
            sys.stdout.write(json.dumps(result))
        except (Unsupported, Clarify, ValueError):
            sys.stdout.write("null")
        raise SystemExit(0)
    context=None
    try:
        question=sys.stdin.read(161)
        event=historical_text(question)
        reader=HistoricalPanchang(calendar)
        value=reader.read(event)
        answer=reader.display(event,value) if mode.endswith("detail") else concise(event,value,label,
            devanagari=any("\u0900"<=c<="\u097f" for c in question))
        instant=event.clock is not None
        ordinal=value["interval"]["ordinal"] if instant else value["sunrise"]
        months=value["months"] if instant else value.get("sunrise_months",{})
        # Never derive a recurrence from an uncertain month or sunrise.
        context=dict(day=event.day.isoformat(),clock=event.clock.isoformat() if instant else None,basis={})
        if ordinal:
            for convention,month in months.items():
                if month:
                    context["basis"][convention]=dict(month=month["month"],intercalation=month["intercalation"],
                        convention=convention,paksha="shukla" if ordinal<=15 else "krishna",
                        tithi=(ordinal-1)%15+1,birth_basis="instant" if instant else "sunrise")
    except (Clarify,Unsupported):
        answer="Māsa, Paksha and Tithi withheld. Check the Delhi date and time or choose a time clear of a transition."
    sys.stdout.write(json.dumps(dict(text=answer,context=context)) if mode.startswith("structured") else answer)
