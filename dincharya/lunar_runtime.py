"""Opt-in acceptance runtime/configuration. Production databases are rejected."""
from pathlib import Path
import argparse
import json
import logging
import os
import stat
import re
from threading import Event, Thread

from dincharya.lunar_service import LunarService,connection_factory,live_transport,envelope
from dincharya.lunar_http import server


def read_private(path):
    path=Path(path)
    root=Path(__file__).resolve().parents[1]
    if path.resolve().is_relative_to(root):raise ValueError('Configuration must be outside Git')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_mode&0o077 or info.st_uid!=os.geteuid() or info.st_nlink!=1:
            raise ValueError('Restricted owner-only regular configuration required')
        raw=os.read(fd,65537)
        if len(raw)>65536:raise ValueError('Configuration too large')
        value=json.loads(raw)
    finally:os.close(fd)
    return value


def validate_test_bot(info,expected_owner):
    if (set(info)!={'token','owner_id','bot_id'} or type(info['owner_id']) is not int
        or not 0<info['owner_id']<2**63 or info['owner_id']!=expected_owner
        or type(info['bot_id']) is not int or not 0<info['bot_id']<2**63
        or not isinstance(info['token'],str)
        or not re.fullmatch(str(info['bot_id'])+r':[A-Za-z0-9_-]{20,100}',info['token'])):
        raise ValueError('Dedicated private test bot/owner pin required')


def build_service(config,*,transport=None,live_approved=False):
    cycle5 = config.get("development_recurring", False)
    if type(cycle5) is not bool or (cycle5 and config.get("development_astronomy") is not True):
        raise ValueError("Recurring development requires isolated astronomy mode")
    historical = config.get("development_historical", False)
    if type(historical) is not bool or (historical and not cycle5):
        raise ValueError("Historical development requires the isolated recurrence service")
    development = config.get("development_astronomy", False)
    if type(development) is not bool:
        raise ValueError("Boolean astronomical development gate required")
    if development and (config.get("delivery_enabled", False) or live_approved or transport is not None):
        raise ValueError("Astronomical development mode requires disabled Telegram transport")
    if type(config.get('delivery_enabled',False)) is not bool:raise ValueError('Boolean delivery gate required')
    if config.get('delivery_enabled',False) and not live_approved:
        raise ValueError('Explicit live transport approval required')
    if type(config.get('owner_id')) is not int or not 0<config['owner_id']<2**63:
        raise ValueError('Explicit private owner required')
    if config.get('delivery_enabled',False):validate_test_bot(config['telegram'],config['owner_id'])
    roles=config['connections']
    if set(roles)!={'owner','calculator','worker'} or len({v['user'] for v in roles.values()})!=3:
        raise ValueError('Separate trusted database logins required')
    connects={k:connection_factory(v) for k,v in roles.items()}
    with connects['owner']() as identity:
        if identity.execute('SELECT lunar_api.owner_identity()').fetchone()[0]!=config['owner_id']:
            raise ValueError('Gateway/database owner identity mismatch')
        calendar, profile = None, None
        if development:
            from prototypes.panchang.guarded import GuardedCalendar

            calendar = GuardedCalendar(config["public_ephemeris"])
            # The existing SQL API also requires the isolated profile to be enabled.
            profile = identity.execute(
                "SELECT encode(sha256(convert_to((%s::jsonb)::text,'UTF8')),'hex')",
                (json.dumps(calendar.specification),),
            ).fetchone()[0]
    if config.get('delivery_enabled',False):
        if not live_approved or transport is not None:raise ValueError('Explicit live transport approval required')
        import httpx
        client=httpx.Client(timeout=10,trust_env=False)
        token=config['telegram']['token'];owner=config['telegram']['owner_id']
        response=client.post('https://api.telegram.org/bot'+token+'/getMe');data=response.json()
        identity=data.get('result',{})
        if (response.status_code!=200 or data.get('ok') is not True or identity.get('id')!=config['telegram']['bot_id']
            or identity.get('username')!='dincharya_acceptance_test_bot'):
            client.close();raise ValueError('Dedicated test bot identity mismatch')
        transport=live_transport(client.post,token,owner,authorized=True)
    service = LunarService(connects['owner'],connects['calculator'],connects['worker'],config['catalog'],
       config['command_key'],config['tick_key'],config['review_key'],transport=transport,
       development_calendar=calendar, development_profile=profile)
    if cycle5:
        from dincharya.recurring import Recurring

        service.development.recurring = Recurring(service.development)
    if historical:
        from dincharya.historical_panchang import HistoricalPanchang

        service.development.historical = HistoricalPanchang(calendar)
    return service


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--live-approved',action='store_true')
    args=parser.parse_args()
    try:
        config=read_private(args.config)
        service=build_service(config,live_approved=args.live_approved)
        stopping = Event()
        projector = None
        if config.get("development_recurring") is True:
            def project():
                import time
                while not stopping.is_set():
                    value, signature = envelope(service.tick_key, {"operation": "project_tick"},
                                                str(time.time_ns()))
                    result = service.handle(value, signature)
                    if result.get("status") not in {"projected", "busy"}:
                        logging.getLogger(__name__).warning("Recurring projection paused until the next check")
                    stopping.wait(300)
            projector = Thread(target=project, daemon=True, name="development-projector")
            projector.start()
        try:
            with server(config['service_socket'], service) as instance:
                instance.serve_forever()
        finally:
            stopping.set()
            if projector:
                projector.join(timeout=5)
    except Exception:raise SystemExit('Lunar acceptance service failed; private details suppressed') from None

if __name__=='__main__':main()
