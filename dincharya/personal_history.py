"""One-shot historical calculation in the accepted, isolated astronomy dependency scope."""
from pathlib import Path
import subprocess
import sys
import sysconfig


def lookup(question,detailed,kernel,wheel):
    from dincharya.attended_runtime import verify_wheel
    verify_wheel(wheel)
    if len(question)>160:
        return "Please give one Delhi date and optional local time."
    r=subprocess.run([sys.executable,"-I","-S","-B",str(Path(__file__).resolve()),str(wheel),
                      str(kernel),"detail" if detailed else "brief"],input=question,text=True,
                     env={"TZ":"UTC"},cwd="/",timeout=30,capture_output=True,close_fds=True)
    if r.returncode or not 0<len(r.stdout)<=4096:
        raise RuntimeError("Historical calculation unavailable")
    return r.stdout


if __name__=="__main__":
    wheel,kernel,mode=sys.argv[1:]
    if not (sys.flags.isolated and sys.flags.no_site and Path(wheel).is_absolute() and Path(kernel).is_absolute()
            and mode in ("detail","brief")):
        raise SystemExit(2)
    sys.path[:0]=[wheel,str(Path(__file__).resolve().parents[1])]
    sys.path.extend([sysconfig.get_path("purelib"),sysconfig.get_path("platlib")])
    from dincharya.daily_review import historical_reply
    from dincharya.lunar_intent import Clarify
    from prototypes.panchang.astronomy import Unsupported
    from prototypes.panchang.guarded import GuardedCalendar
    try:
        answer=historical_reply(sys.stdin.read(161),GuardedCalendar(Path(kernel)),detailed=mode=="detail")
    except (Clarify,Unsupported):
        answer="The requested Delhi date or time needs clarification or is outside the validated calendar profile."
    sys.stdout.write(answer)
