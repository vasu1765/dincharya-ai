"""Pure acceptance checks; never change worker lookback, leases or delivery state."""
import math

PHASES = ('prepare', 'arm', 'interrupt', 'recover', 'verify', 'export')
OVERDUE = {'Recovery Outage A', 'Recovery Outage B'}
LOST = 'Staging uncertain'


def require(ok, category):
    if not ok:
        raise ValueError(category)


def next_phase(started, done):
    require(set(started) <= set(PHASES) and set(done) <= set(started), 'invalid journal')
    count = len(done)
    require(set(done) == set(PHASES[:count]) and set(started) == set(done),
            'uncertain or nonsequential phase; inspect without replay')
    return PHASES[count] if count < len(PHASES) else None


def performance(stopped, ready):
    require(all(math.isfinite(x) for x in (stopped, ready)) and ready >= stopped, 'invalid clock')
    seconds = ready-stopped
    return {'stop_to_ready_seconds': seconds, 'within_600_seconds': seconds <= 600}


def evidence(rows, attempts, due, completed, ready=None, stopped=None, recovery_started=None):
    require(len(rows) == len(due) and len({r[0] for r in rows}) == len(rows)
            and {r[0] for r in rows} == set(due), 'unexpected slots')
    require(len(attempts) == len(completed) and {a[2] for a in attempts} == set(completed)
            and len({a[0] for a in attempts}) == len(attempts), 'duplicate or unexpected attempt')
    by_title = {a[2]: a for a in attempts}
    for title, status, count, chat, receipt, when_due in rows:
        require(when_due == due[title], 'changed due time')
        if title not in completed:
            require((status,count,chat,receipt) == ('pending',0,None,None), 'premature attempt')
            continue
        mid, uncertain, _, sent = by_title[title]
        require(math.isfinite(sent) and sent >= when_due, 'premature or invalid delivery')
        if title in OVERDUE:
            require(ready is not None and stopped is not None and recovery_started is not None
                    and stopped <= recovery_started <= ready
                    and stopped < when_due <= recovery_started and sent >= recovery_started
                    and sent <= ready+120 and sent-when_due <= 21600,
                    'invalid overdue catch-up')
        else:
            require(sent <= when_due+180, 'ordinary delivery outside window')
        expected = ('uncertain',1,None,None) if title == LOST else ('sent',1,101,mid)
        require(type(mid) is int and mid > 0 and uncertain == int(title == LOST)
                and (status,count,chat,receipt) == expected, 'receipt or attempt mismatch')


def observer_evidence(rows, revision, armed, stopped, ready):
    from datetime import datetime
    require(rows and all(r.get('revision') == revision and
            r.get('project') == 'dincharya-stage2-recovery-only' for r in rows), 'observer target')
    samples = [(datetime.fromisoformat(r['utc']).timestamp(), r['state']) for r in rows]
    require(all(0 < b[0]-a[0] <= 35 for a,b in zip(samples,samples[1:])), 'observer cadence')
    initial = [(t,s) for t,s in samples if armed-60 <= t <= armed]
    require(len(initial) >= 3 and all(s == 'ready' for _,s in initial[-3:])
            and armed-initial[-1][0] <= 30, 'observer pre-arm evidence')
    require(any(stopped <= t <= ready and s == 'outage' for t,s in samples), 'observer outage')
    require(any(ready <= t <= ready+45 and s == 'ready' for t,s in samples), 'observer recovery')
