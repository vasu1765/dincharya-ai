"""Internal-only synthetic staging services. No Telegram network transport."""
import asyncio
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import secrets
import signal
import sqlite3
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT),str(ROOT/'telegram-gateway'),str(ROOT/'tests/integration')]
from dincharya.reminders import DeliveryReceipt, process_batch

BEAT = Path('/tmp/laptop-heartbeat')
STOP = threading.Event()
URL = 'http://relay:5678/webhook/m2g-lunar'


def beat():
    tmp=BEAT.with_suffix('.tmp')
    tmp.write_text(str(time.monotonic()))
    tmp.replace(BEAT)


class Recorder:
    def __init__(self, path):
        self.path = path
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, uncertain INTEGER NOT NULL)')

    def send(self, payload):
        uncertain = payload['title'] == 'Staging uncertain'
        with sqlite3.connect(self.path) as db:
            row = db.execute('INSERT INTO attempts(uncertain) VALUES (?)',(uncertain,))
            receipt = row.lastrowid
        if uncertain:
            raise TimeoutError('Synthetic lost acknowledgement')
        return DeliveryReceipt(101,receipt)


def worker(config):
    from dincharya.lunar_service import connection_factory
    from dincharya.reminder_adapters import PostgresReminders
    from dincharya.reminders import DeliveryUncertain
    connect=connection_factory(config)
    store=PostgresReminders(connect,notification_slots=True)
    transport=Recorder('/record/attempts.sqlite')
    with connect() as lease:
        lease.commit()
        lease.autocommit=True
        if not lease.execute('SELECT pg_try_advisory_lock(20261112,3)').fetchone()[0]:
            raise ValueError('Worker busy')
        while not STOP.is_set():
            lease.execute('SELECT 1')
            try:
                done=process_batch(store,transport,lambda:datetime.now(timezone.utc),limit=1)
            except DeliveryUncertain:
                print('{"worker":"quarantine"}',flush=True)
                done=0
            beat()
            STOP.wait(1 if done else 5)


def probe(config):
    import httpx
    from lunar_handlers import OrchestrationClient
    with httpx.Client(timeout=6,trust_env=False) as client:
        relay=OrchestrationClient(client,URL,config['key'])
        result=relay.call({'operation':'list_lunar_annual','after':None},secrets.token_hex(12))
        if result.get('status')!='listed':
            raise ValueError('Relay unavailable')
        health=relay.call({'operation':'recurring_health'},secrets.token_hex(12))
        if health.get('status')!='health':
            raise ValueError('Health unavailable')
    return dict(relay='ready', **{k:int(health['health'][k]) for k in ('due','uncertain','dead','sending')})


def install():
    import httpx
    flow=json.loads((ROOT/'workflows/m2g-lunar-acceptance.json').read_text())
    if flow['active'] or [n['type'] for n in flow['nodes']] != ['n8n-nodes-base.webhook','n8n-nodes-base.httpRequest']:
        raise ValueError('Unexpected relay')
    params=flow['nodes'][1]['parameters']
    params['url']='http://app:8080/lunar'
    params['options']={'timeout':40000,'response':{'response':{'neverError':True,'responseFormat':'json'}}}
    with httpx.Client(base_url='http://relay:5678',trust_env=False,timeout=10) as c:
        for _ in range(60):
            try:
                if c.get('/healthz/readiness').is_success:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(1)
        c.post('/rest/owner/setup',json=dict(email='fixture@example.invalid',firstName='Test',lastName='Owner',
            password='X9'+secrets.token_urlsafe(30))).raise_for_status()
        result=c.post('/rest/workflows',json=flow)
        result.raise_for_status()
        record=result.json()['data']
        c.post('/rest/workflows/'+record['id']+'/activate',json={'versionId':record['versionId']}).raise_for_status()


async def gateway(config):
    import httpx
    from telegram import Update
    from telegram.ext import Application
    from m2g_bot import OfflineBotAPI
    from lunar_handlers import OrchestrationClient, register_lunar_previews

    class Wire(OfflineBotAPI):
        async def do_request(self,url,method,request_data=None,**kw):
            if url.endswith('/answerCallbackQuery'):
                return 200,b'{"ok":true,"result":true}'
            if url.endswith('/sendMessage'):
                self.markup=request_data.parameters.get('reply_markup')
            return await super().do_request(url,method,request_data,**kw)

    wire=Wire()
    client=httpx.Client(timeout=45,trust_env=False)
    app=Application.builder().token('123456:offline').request(wire).get_updates_request(Wire()).build()
    register_lunar_previews(app,101,OrchestrationClient(client,URL,config['key']),recurring=True)
    await app.initialize()
    guard=asyncio.Lock()
    async def handle(reader,writer):
        try:
            raw=await asyncio.wait_for(reader.readline(),5)
            async with guard:
                wire.messages.clear()
                wire.markup=None
                await app.process_update(Update.de_json(json.loads(raw),app.bot))
                writer.write(json.dumps(dict(messages=wire.messages,keyboard=wire.markup)).encode()+b'\n')
                await writer.drain()
        finally:
            writer.close()
    server=await asyncio.start_server(handle,'127.0.0.1',9200,limit=8192)
    try:
        while not STOP.is_set():
            await asyncio.to_thread(probe,config)
            beat()
            await asyncio.sleep(5)
    finally:
        server.close()
        await server.wait_closed()
        await app.shutdown()
        client.close()


def main():
    role=sys.argv[1]
    if role=='health':
        if not BEAT.exists() or not 0 <= time.monotonic()-float(BEAT.read_text()) < 30:
            sys.exit(1)
        return
    if role=='install':
        return install()
    if role=='inject':
        import socket
        with socket.create_connection(('127.0.0.1',9200),timeout=50) as sock:
            sock.sendall(sys.stdin.buffer.readline(8192).rstrip()+b'\n')
            print(sock.makefile().readline().strip())
        return
    config=json.loads(Path('/cfg.json').read_text())
    signal.signal(signal.SIGTERM,lambda *_: STOP.set())
    if role=='probe':
        print(json.dumps(probe(config)))
    elif role=='gateway':
        asyncio.run(gateway(config))
    elif role=='worker':
        worker(config)
    elif role=='app':
        from dincharya.lunar_runtime import build_service
        from dincharya.lunar_http import request_handler
        service=build_service(config)
        with ThreadingHTTPServer(('0.0.0.0',8080),request_handler(service)) as server:
            server.timeout=1
            next_projection=0
            while not STOP.is_set():
                if time.monotonic()>=next_projection:
                    from dincharya.lunar_service import envelope
                    value,signature=envelope(service.tick_key,{'operation':'project_tick'},secrets.token_hex(12))
                    if service.handle(value,signature).get('status') not in ('projected','busy'):
                        raise ValueError('Projection unavailable')
                    next_projection=time.monotonic()+300
                server.handle_request()
                beat()
    else:
        raise ValueError('Unknown role')


if __name__=='__main__':
    logging.disable(logging.CRITICAL)
    try:
        main()
    except Exception:
        sys.exit('{"stage":"unavailable"}')
