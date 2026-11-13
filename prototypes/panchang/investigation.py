"""Controlled astronomy hypotheses, never an adopted calendar or scheduling API.

ERFA implements published IAU matrices. No Swiss Ephemeris code is imported.
"""
from datetime import datetime,timedelta
import math
import numpy as np
import erfa
from skyfield.framelib import ecliptic_frame,ecliptic_J2000_frame,ICRS_to_J2000
from skyfield.functions import mxm,rot_x

from .astronomy import Astronomy,UTC,Unsupported,aware,iso

PROFILE = 'lahiri1956-true-plus0.658as-iau1976-nut1980-fixed-origin-v1'


class MeanDateFrame:
    def rotation_at(self,t):
        return mxm(rot_x(-t._mean_obliquity_radians),t.P)


class ControlledAstronomy(Astronomy):
    """Research-only position/frame selection; baseline defaults unchanged."""
    def __init__(self,ephemeris,position,frame):
        if position not in ('apparent','astrometric','geometric') or frame not in ('true_date','mean_date','J2000'):
            raise Unsupported('Unknown controlled convention')
        self.position_mode=position
        self.coordinate_frame={'true_date':ecliptic_frame,'mean_date':MeanDateFrame(),'J2000':ecliptic_J2000_frame}[frame]
        super().__init__(ephemeris)

    def _longitudes(self,tt):
        t=self.ts.tt_jd(tt)
        center=self.earth.at(t)
        result=[]
        for body in (self.sun,self.moon):
            point=(body-self.earth).at(t) if self.position_mode=='geometric' else center.observe(body)
            if self.position_mode=='apparent': point=point.apparent()
            result.append(point.frame_latlon(self.coordinate_frame)[1].degrees)
        if not np.all(np.isfinite(result)):
            raise Unsupported('Nonfinite controlled convention')
        return result


def true_ecliptic76_80(jd_tt):
    """J2000 mean equator -> true ecliptic of date, IAU1976 / IAU1980."""
    delta=jd_tt-2451545.0
    dp,de=erfa.nut80(2451545.0,delta)
    epsilon=erfa.obl80(2451545.0,delta)
    return rot_x(-(epsilon+de))@erfa.numat(epsilon,dp,de)@erfa.pmat76(2451545.0,delta)


class LahiriHypothesis:
    """Explicit epoch-anchored candidate; NOT month_label/annual-preview enablement.

    Fixed J2000-mean direction has true tropical longitude 23d15m00.658s
    at JD(TT)2435553.5. Transport with the stated matrices, not constant drift.
    Also allow the uncorrected 23d15m anchor as a separately measured control.
    """
    def __init__(self,astronomy,correction_arcsec=.658):
        if correction_arcsec not in (0.0,.658):
            raise Unsupported('Unreviewed Lahiri anchor variant')
        self.a=astronomy
        self.correction_arcsec=correction_arcsec
        anchor=np.deg2rad(23.25+correction_arcsec/3600)
        self.origin=true_ecliptic76_80(2435553.5).T@np.array([np.cos(anchor),np.sin(anchor),0.0])

    def ayanamsa_at(self,instant):
        t=self.a.ts.from_datetime(aware(instant))
        v=true_ecliptic76_80(t.tt)@self.origin
        return float(np.rad2deg(np.arctan2(v[1],v[0]))%360)

    def solar_longitude(self,instant):
        instant=aware(instant)
        t=self.a.ts.from_datetime(instant)
        R=true_ecliptic76_80(t.tt)
        p=R@(ICRS_to_J2000@self.a.earth.at(t).observe(self.a.sun).apparent().position.au)
        origin=R@self.origin
        longitude=(np.rad2deg(np.arctan2(p[1],p[0]))-
                   np.rad2deg(np.arctan2(origin[1],origin[0])))%360
        if not math.isfinite(longitude) or not 0<=longitude<360:
            raise Unsupported('Ambiguous sidereal solar longitude')
        return float(longitude)

    def solar_ingresses(self,start,end):
        start,end=aware(start),aware(end)
        if not start<end or end-start>timedelta(days=370):
            raise Unsupported('Unsupported solar research interval')
        result=[]
        low=start
        previous=self.solar_longitude(low)
        while low<end:
            high=min(end,low+timedelta(days=1))
            current=self.solar_longitude(high)
            advance=(current-previous)%360
            if not 0<advance<2:
                raise Unsupported('Ambiguous daily solar bracket')
            if int(previous/30)!=int(current/30):
                target=int(current/30)*30
                a,b=low,high
                while (b-a).total_seconds()>.05:
                    middle=a+(b-a)/2
                    if (self.solar_longitude(middle)-target+180)%360-180>=0:
                        b=middle
                    else: a=middle
                result.append(dict(at=iso(b),sign=int(target/30)))
            low,previous=high,current
        return result

    def amanta_diagnostic(self,instant):
        bounds=self.a.month_boundaries(instant,'amanta')
        start,end=[datetime.fromisoformat(bounds[k]) for k in ('start','end')]
        nearby=self.solar_ingresses(start-timedelta(days=1),end+timedelta(days=1))
        ingresses=[r for r in nearby if start<datetime.fromisoformat(r['at'])<=end]
        if len(ingresses)>1:
            raise Unsupported('Kshaya or multiple-ingress month naming is unsupported')
        if any(min(abs((datetime.fromisoformat(r['at'])-start).total_seconds()),
                   abs((end-datetime.fromisoformat(r['at'])).total_seconds()))<=120 for r in nearby):
            raise Unsupported('Solar ingress near month boundary requires review')
        # Research naming rule for only the simple zero/one-ingress cases.
        months=('chaitra','vaishakha','jyeshtha','ashadha','shravana','bhadrapada',
                'ashvina','kartika','margashirsha','pausha','magha','phalguna')
        number=(int(self.solar_longitude(start)/30)+1)%12
        return dict(start=bounds['start'],end=bounds['end'],candidate_amanta_month=months[number],
                    candidate_intercalation='adhika' if not ingresses else 'ordinary',
                    ingress_count=len(ingresses),ingresses=ingresses,profile=PROFILE,
                    status='research_only_not_calendar_enablement')
