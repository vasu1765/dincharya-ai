"""Print older ciphertext candidates for owner review; retain seven dates and four ISO weeks."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import re


def candidates(directory):
    entries=[]
    for path in directory.iterdir():
        if re.fullmatch(r"[a-f0-9]{64}\.cms",path.name) and not path.is_symlink() and path.is_file():
            entries.append((path.stat().st_mtime,path))
    days,weeks=set(),set()
    for stamp,path in sorted(entries,reverse=True):
        day=datetime.fromtimestamp(stamp,timezone.utc).date()
        week=day.isocalendar()[:2]
        daily=day not in days and len(days)<7
        weekly=week not in weeks and len(weeks)<4
        if daily:
            days.add(day)
        if weekly:
            weeks.add(week)
        if not daily and not weekly:
            yield path.name


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    for name in candidates(parser.parse_args().directory):
        print(name)
