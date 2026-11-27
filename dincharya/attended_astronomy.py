"""One question per isolated child; no Telegram client or service credentials."""
from pathlib import Path
import sys
import sysconfig


def main():
    wheel, kernel = map(Path, sys.argv[1:])
    if not (sys.flags.isolated and sys.flags.no_site and wheel.is_absolute() and kernel.is_absolute()):
        raise ValueError("Isolated astronomy invocation required")
    sys.path[:0] = [str(wheel), str(Path(__file__).resolve().parents[1])]
    sys.path.extend([sysconfig.get_path("purelib"), sysconfig.get_path("platlib")])
    from dincharya.historical_panchang import HistoricalPanchang, historical_text
    from prototypes.panchang.guarded import GuardedCalendar
    question = sys.stdin.read(161)
    if len(question) > 160:
        raise ValueError("Historical question too long")
    event = historical_text(question)
    reader = HistoricalPanchang(GuardedCalendar(kernel))
    sys.stdout.write(reader.display(event, reader.read(event)))


if __name__ == "__main__":
    main()
