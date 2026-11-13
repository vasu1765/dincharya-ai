"""Experimental local-file astronomy only. No DB, HTTP, festival or delivery API."""
from datetime import date, datetime, timedelta, timezone
import hashlib
import importlib.metadata
from io import BytesIO
import json
import math
import os
from pathlib import Path
import stat
from zoneinfo import ZoneInfo

import numpy as np
from skyfield import almanac
from skyfield.api import load, wgs84
from skyfield.framelib import ecliptic_frame
from skyfield.jpllib import SpiceKernel
import skyfield

UTC = timezone.utc
TZDATA = Path('/usr/share/zoneinfo/Asia/Kolkata').read_bytes()
DELHI = ZoneInfo.from_file(BytesIO(TZDATA),key='Asia/Kolkata')
MINIMUM = datetime(1900, 1, 1, tzinfo=UTC)
MAXIMUM = datetime(2101, 1, 1, tzinfo=UTC)
METADATA = Path(__file__).with_name('ephemeris.json')
MODELS = {'upper_limb_50': -50 / 60, 'pac_47_hypothesis': -47 / 60}


class Unsupported(ValueError):
    """Sanitized fail-closed prototype result, never a scheduling fallback."""


def aware(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise Unsupported('An explicit timezone-aware instant is required')
    try:
        value = value.astimezone(UTC)
    except (ValueError,OverflowError):
        raise Unsupported('Unsupported instant conversion') from None
    if not MINIMUM <= value < MAXIMUM:
        raise Unsupported('Supported instant range is 1900 through 2100 UTC')
    return value


def iso(value):
    return value.astimezone(UTC).isoformat(timespec='microseconds')


def valid_tithi(value):
    if type(value) is not int or not 1 <= value <= 30:
        raise Unsupported('Tithi ordinal must be an integer from 1 through 30')


class Astronomy:
    latitude = 28.6139
    longitude = 77.2090
    boundary_guard_seconds = 120

    def __init__(self, ephemeris):
        self._fd = None
        self.eph = None
        self._sunrises = {}
        self.metadata = json.loads(METADATA.read_text())
        try:
            if hashlib.sha256(TZDATA).hexdigest()!=self.metadata['timezone_tzif_sha256']:
                raise Unsupported('Pinned timezone data mismatch')
            for name, expected in self.metadata['dependencies'].items():
                if importlib.metadata.version(name) != expected:
                    raise Unsupported('Dependency version differs from the reviewed lock')
            data = Path(skyfield.__file__).parent / 'data'
            for name, expected in self.metadata['skyfield_data_sha256'].items():
                if hashlib.sha256((data / name).read_bytes()).hexdigest() != expected:
                    raise Unsupported('Pinned timescale or astronomy data mismatch')
            self._fd = os.open(ephemeris, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            info = os.fstat(self._fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size != self.metadata['size_bytes']:
                raise Unsupported('Expected regular DE440s data file with pinned size')
            digest = hashlib.sha256()
            with os.fdopen(os.dup(self._fd), 'rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            if digest.hexdigest() != self.metadata['sha256']:
                raise Unsupported('Pinned DE440s digest mismatch')
            # Open the verified inode, not a second resolution of caller's path.
            # Linux-only feasibility target; the original fd stays open.
            self.eph = SpiceKernel(f'/proc/self/fd/{self._fd}')
            self.ts = load.timescale(builtin=True)
            self.earth, self.sun, self.moon = self.eph['earth'], self.eph['sun'], self.eph['moon']
            self.observer = self.earth + wgs84.latlon(self.latitude, self.longitude, elevation_m=0)
        except Unsupported:
            self.close()
            raise
        except Exception:
            self.close()
            raise Unsupported('Pinned local astronomy data unavailable; no download or fallback') from None

    def close(self):
        if self.eph is not None:
            self.eph.close()
            self.eph = None
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _longitudes(self, tt):
        t = self.ts.tt_jd(tt)
        center = self.earth.at(t)
        sun = center.observe(self.sun).apparent().frame_latlon(ecliptic_frame)[1].degrees
        moon = center.observe(self.moon).apparent().frame_latlon(ecliptic_frame)[1].degrees
        if not np.all(np.isfinite(sun)) or not np.all(np.isfinite(moon)):
            raise Unsupported('Nonfinite astronomy result')
        return sun, moon

    def _elongation(self, tt):
        sun, moon = self._longitudes(tt)
        result = (moon - sun) % 360
        # Floating modulo of a tiny negative number can round UP to 360.
        # Do not return ordinal 31 or silently choose a side of that boundary.
        if not np.all(np.isfinite(result)) or np.any(result<0) or np.any(result>=360):
            raise Unsupported('Elongation is nonfinite or indistinguishable from wrap')
        return result

    def elongation(self, instant):
        return float(self._elongation(self.ts.from_datetime(aware(instant)).tt))

    def tithi_at(self, instant):
        return int(math.floor(self.elongation(instant) / 12)) + 1

    def _transitions(self, start, end):
        """Find every 12-degree crossing; vectorized bisection, <=0.05 s bracket.

        Internal callers may pad public intervals by up to 40 days, still within
        DE440s. Six-hour samples must bracket exactly one or zero transitions.
        """
        first, last = self.ts.from_datetime(start).tt, self.ts.from_datetime(end).tt
        if last<=first:
            raise Unsupported('Search interval is below timescale precision')
        samples = np.linspace(first, last, max(2, math.ceil((last-first)*4)+1))
        phases = self._elongation(samples)
        bins = np.floor(phases / 12).astype(int)
        advance = np.diff(phases) % 360
        if np.any(advance<=0) or np.any(advance>=12):
            raise Unsupported('Ambiguous six-hour sample motion')
        jumps = (np.diff(bins) % 30)
        if np.any(jumps > 1):
            raise Unsupported('Ambiguous transition bracket')
        indices = np.flatnonzero(jumps == 1)
        low, high = samples[indices].copy(), samples[indices+1].copy()
        targets = ((bins[indices]+1)*12) % 360
        while len(low) and float(np.max(high-low))*86400 > 0.05:
            middle = (low+high)/2
            difference = (self._elongation(middle)-targets+180) % 360-180
            high = np.where(difference >= 0, middle, high)
            low = np.where(difference < 0, middle, low)
        return [dict(at=iso(self.ts.tt_jd(float(t)).utc_datetime()),
                     ordinal=int(target/12)+1, bracket_seconds=float((t-l)*86400))
                for t, l, target in zip(high, low, targets)]

    def transitions(self, start, end):
        """Transitions in (start,end], allowing MAXIMUM only as end sentinel."""
        start = aware(start)
        if not isinstance(end, datetime) or end.tzinfo is None or end.utcoffset() is None:
            raise Unsupported('An explicit timezone-aware interval is required')
        try:
            end = end.astimezone(UTC)
        except (ValueError,OverflowError):
            raise Unsupported('Unsupported interval endpoint') from None
        if not start < end <= MAXIMUM or end-start > timedelta(days=370):
            raise Unsupported('Transition interval must be ordered, supported and at most 370 days')
        # Search endpoint membership is also ambiguous within solver precision.
        # Inspect tiny internal pads; never expose them as public calendar claims.
        for endpoint in (start,end):
            nearby=self._transitions(endpoint-timedelta(seconds=.2),endpoint+timedelta(seconds=.2))
            if any(abs((datetime.fromisoformat(r['at'])-endpoint).total_seconds())<=.1 for r in nearby):
                raise Unsupported('Search endpoint is inside numerical transition uncertainty')
        return [row for row in self._transitions(start,end)
                if start<datetime.fromisoformat(row['at'])<=end]

    @staticmethod
    def _complete_bounds(start,end):
        if not MINIMUM<=start<end<=MAXIMUM:
            raise Unsupported('Complete interval is outside supported range; padding is not a calendar claim')

    def tithi_interval(self, instant):
        instant = aware(instant)
        transitions = self._transitions(instant-timedelta(days=2), instant+timedelta(days=2))
        if any(abs((datetime.fromisoformat(r['at'])-instant).total_seconds())<=0.1 for r in transitions):
            raise Unsupported('Instant is inside numerical transition uncertainty')
        before = [row for row in transitions if datetime.fromisoformat(row['at']) <= instant]
        after = [row for row in transitions if datetime.fromisoformat(row['at']) > instant]
        if not before or not after:
            raise Unsupported('Unbracketed tithi interval')
        start, end = before[-1], after[0]
        self._complete_bounds(datetime.fromisoformat(start['at']),datetime.fromisoformat(end['at']))
        ordinal = self.tithi_at(instant)
        if ordinal != start['ordinal']:
            # A solved transition has finite numerical uncertainty; never return
            # an internally contradictory interval at that boundary.
            raise Unsupported('Instant is inside numerical transition uncertainty')
        distance = min((instant-datetime.fromisoformat(start['at'])).total_seconds(),
                       (datetime.fromisoformat(end['at'])-instant).total_seconds())
        return dict(start=start['at'],end=end['at'],ordinal=ordinal,
                    paksha='shukla' if ordinal<=15 else 'krishna',paksha_day=(ordinal-1)%15+1,
                    review_required=distance<=self.boundary_guard_seconds)

    def sunrise(self, day, model='upper_limb_50'):
        if (type(day) is not date or not 1900 <= day.year <= 2100
                or not isinstance(model,str) or model not in MODELS):
            raise Unsupported('Unsupported civil date or sunrise hypothesis')
        key = (day,model)
        if key not in self._sunrises:
            start = datetime.combine(day,datetime.min.time(),DELHI).astimezone(UTC)
            times, found = almanac.find_risings(self.observer,self.sun,
                self.ts.from_datetime(start),self.ts.from_datetime(start+timedelta(days=1)),
                horizon_degrees=MODELS[model])
            if len(times)!=1 or not bool(found[0]):
                raise Unsupported('Missing or ambiguous sunrise')
            self._sunrises[key] = aware(times[0].utc_datetime())
        return self._sunrises[key]

    def at_sunrise(self, day, model='upper_limb_50'):
        sunrise = self.sunrise(day,model)
        # The public lower instant boundary excludes pre-UTC-1900 only; Delhi's
        # sunrise on Jan 1 1900 is inside the supported interval.
        return dict(date=day.isoformat(),sunrise=iso(sunrise),model=model,
                    calendar_status='experimental_sunrise_model',**self.tithi_interval(sunrise))

    def month_boundaries(self, instant, convention='purnimanta'):
        instant = aware(instant)
        if convention not in ('amanta','purnimanta'):
            raise Unsupported('Unknown month convention')
        ordinal = 1 if convention=='amanta' else 16
        rows = [r for r in self._transitions(instant-timedelta(days=40),instant+timedelta(days=40))
                if r['ordinal']==ordinal]
        if any(abs((datetime.fromisoformat(r['at'])-instant).total_seconds())<=.1 for r in rows):
            raise Unsupported('Instant is inside numerical month-boundary uncertainty')
        before = [r for r in rows if datetime.fromisoformat(r['at'])<=instant]
        after = [r for r in rows if datetime.fromisoformat(r['at'])>instant]
        if not before or not after:
            raise Unsupported('Unbracketed lunar month boundaries')
        self._complete_bounds(datetime.fromisoformat(before[-1]['at']),datetime.fromisoformat(after[0]['at']))
        return dict(convention=convention,start=before[-1]['at'],end=after[0]['at'],
                    month_name=None,intercalation_status='unsupported_without_validated_ayanamsa')

    def month_label(self, instant, convention='purnimanta'):
        self.month_boundaries(instant,convention)
        raise Unsupported('Exact Lahiri/month naming and exceptional Purnimanta conversion are not validated')

    def lunation_diagnostics(self, instant):
        """Sensitivity experiment only: constant offsets are NOT Lahiri.

        Agreement under these offsets supports a known-period investigation,
        never a verified named calendar month or general Adhika detection API.
        """
        bounds = self.month_boundaries(instant,'amanta')
        start,end = (self.ts.from_datetime(datetime.fromisoformat(bounds[k])).tt for k in ('start','end'))
        sun = self._longitudes(np.array([start,end]))[0]
        advance = float((sun[1]-sun[0]) % 360)
        counts = {}
        for offset in (24.0,24.2,24.5):
            beginning = float((sun[0]-offset) % 360)
            counts[str(offset)] = math.floor((beginning+advance)/30)-math.floor(beginning/30)
        return dict(**bounds,tropical_sun_start=float(sun[0]),tropical_sun_end=float(sun[1]),
                    constant_offset_ingress_counts=counts,
                    status='unvalidated_hypothesis_not_lahiri_or_named_month')

    def monthly_preview(self, ordinal, start_day, end_day):
        """Ephemeral personal/generic tithi preview only; no schedule persistence."""
        valid_tithi(ordinal)
        if (type(start_day) is not date or type(end_day) is not date
                or not date(1900,1,1)<=start_day<end_day<=date(2101,1,1)
                or not 0 < (end_day-start_day).days <= 366):
            raise Unsupported('Preview must be ordered and bounded to 366 civil days')
        start = datetime.combine(start_day,datetime.min.time(),DELHI).astimezone(UTC)
        end = datetime.combine(end_day,datetime.min.time(),DELHI).astimezone(UTC)
        rows = self._transitions(start-timedelta(days=2),end+timedelta(days=2))
        result = []
        for first,last in zip(rows,rows[1:]):
            if first['ordinal']!=ordinal:
                continue
            a,b = datetime.fromisoformat(first['at']),datetime.fromisoformat(last['at'])
            if b<=start or a>=end:
                continue
            self._complete_bounds(a,b)
            dates=[]; nearby=False
            day=a.astimezone(DELHI).date()
            while day<=b.astimezone(DELHI).date():
                if day>=date(2101,1,1):
                    break  # This sunrise must be beyond MAXIMUM UTC for Delhi.
                sunrise=self.sunrise(day)
                if min(abs((sunrise-a).total_seconds()),abs((sunrise-b).total_seconds()))<=120:
                    nearby=True
                if a<=sunrise<b:
                    dates.append(day)
                day+=timedelta(days=1)
            anchor=dates[0] if dates else a.astimezone(DELHI).date()
            if start_day<=anchor<end_day:
                review = nearby or not dates
                result.append(dict(ordinal=ordinal,start=iso(a),end=iso(b),
                    sunrise_dates=[d.isoformat() for d in dates],
                    selected_date=None if review else anchor.isoformat(),
                    status='needs_review' if review else 'experimental_first_sunrise',
                    reason='boundary_uncertainty' if nearby else 'skipped_at_sunrise' if not dates
                           else 'first_of_repeated_sunrises' if len(dates)>1 else 'single_sunrise'))
        return result

    def annual_preview(self, *_, **__):
        raise Unsupported('Annual lunar anniversaries require validated month names; no dates guessed')
