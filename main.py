from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel
from logger import log
import httpx
import json
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(update_cache())
    yield

app = FastAPI(lifespan=lifespan)

class AgentPayload(BaseModel):
    IP: str
    PUBLIC_IP: str
    NAME: str
    PORT: int
    SERVICES: list
    LS: int

class ErrorCl(BaseModel):
    IP: str
    LEVEL: str
    MSG: str

SERVERS = {}
cache = {}

async def fetch_agent(client, ip, port, destination):
    try:
        res = await client.get(f'http://{ip}:{port}/{destination}', timeout=3)
        if res.status_code == 200 and res.content:
            return ip, res.json()
        return ip, None
    except (httpx.RequestError, Exception):
        return ip, None

async def collect_all():
    if SERVERS != {}:
        async with httpx.AsyncClient() as client:
            tasks = []
            for data in SERVERS.values():
                tasks.append(fetch_agent(client, data['IP'], data['PORT'], 'current'))
            result = await asyncio.gather(*tasks)
        for ip, data in result:
            cache[ip] = data

async def update_cache():
    while True:
        await collect_all()
        await asyncio.sleep(5)

@app.post('/reg_agent')
async def reg_agent(payload: AgentPayload):
    if payload.IP not in SERVERS:
        log('info', 'Contoller', f'{payload.IP} firsts seen this time')
    SERVERS[payload.IP] = payload.model_dump()
    print(SERVERS)
    return {'ok': True}

@app.post('/send_error')
async def get_error(error: ErrorCl):
    log(error.LEVEL, 'agent', f'{error.IP}: {error.MSG}')

@app.get('/servers')
async def servers():
    return {'ok': True, 'data': SERVERS}

@app.get('/current')
async def get_current():
    return {'ok': True, 'data': cache}

@app.get('/server/{ip}')
async def get_server(ip: str):
    if ip in cache:
        return {'ok': True, 'data': cache.get(ip)}
    return {'ok': False, 'error': 'ip_not_exists'}

@app.post('/agent/{ip}/service/{name}/{action}')
async def server_action(ip: str, name: str, action: str):
    if ip in SERVERS:
        if name in SERVERS[ip].get('SERVICES'):
            async with httpx.AsyncClient() as client:
                res = await client.post(f'http://{ip}:8888/service/{name}/{action}', timeout=5)
                return res.json()
        return {'ok': False, 'error': 'service_not_registered'}
    return {'ok': False, 'error': 'server_not_registered'}

@app.post('/agent/{ip}/nginx/{action}')
async def nginx_post(ip: str, action: str, request: Request):
    if 'nginx' not in SERVERS[ip].get('SERVICES'):
        return {'ok': False, 'error': 'service_not_registered'}
    body = await request.json() if request.headers.get('content-type') else None
    async with httpx.AsyncClient() as client:
        if body:
            res = await client.post(f'http://{ip}:8888/nginx/{action}', json=body, timeout=5)
        else:
            res = await client.post(f'http://{ip}:8888/nginx/{action}', timeout=5)
        return res.json()

@app.get('/agent/{ip}/nginx/{action}')
async def nginx_get(ip: str, action: str):
    if 'nginx' not in SERVERS[ip].get('SERVICES'):
        return {'ok': False, 'error': 'service_not_registered'}
    async with httpx.AsyncClient() as client:
        res = await client.get(f'http://{ip}:8888/nginx/{action}', timeout=5)
        return res.json()

@app.websocket('/live/metrics/{ip}')
async def live(websocket: WebSocket, ip: str):
    await websocket.accept()
    async with httpx.AsyncClient() as client:
        try:
            while True:
                try:
                    res = await client.get(f'http://{ip}:8888/metrics', timeout=3)
                    await websocket.send_json({'ok': True, 'data': res.json()})
                except WebSocketDisconnect:
                    return
                except:
                    await websocket.send_json({'ok': False, 'error':'offline'})
                await asyncio.sleep(0.5)
        except WebSocketDisconnect:
            return

@app.websocket('/live/services/{ip}')
async def live(websocket: WebSocket, ip: str):
    await websocket.accept()
    async with httpx.AsyncClient() as client:
        try:
            while True:
                try:
                    res = await client.get(f'http://{ip}:8888/services', timeout=3)
                    await websocket.send_json({'ok': True, 'data': res.json()})
                except WebSocketDisconnect:
                    return
                except:
                    await websocket.send_json({'ok': False, 'error':'offline'})
                await asyncio.sleep(0.5)
                
        except WebSocketDisconnect:
            return
        
@app.websocket('/live/metrics')
async def live(websocket: WebSocket):
    await websocket.accept()
    async with httpx.AsyncClient() as client:
        try:
            while True:
                tasks = []
                for data in SERVERS.values():
                    tasks.append(fetch_agent(client, data['IP'], data['PORT'], 'metrics'))
                result = await asyncio.gather(*tasks)
                try:
                    await websocket.send_json({'ok': True, 'data': {ip: data for ip, data in result}})
                except WebSocketDisconnect:
                    return
                await asyncio.sleep(0.5)
        except WebSocketDisconnect:
            return

@app.websocket('/live/services')
async def live(websocket: WebSocket):
    await websocket.accept()
    async with httpx.AsyncClient() as client:
        try:
            while True:
                tasks = []
                for data in SERVERS.values():
                    tasks.append(fetch_agent(client, data['IP'], data['PORT'], 'services'))
                result = await asyncio.gather(*tasks)
                try:
                    await websocket.send_json({'ok': True, 'data': {ip: data for ip, data in result}})
                except WebSocketDisconnect:
                    return
                await asyncio.sleep(0.5)
        except WebSocketDisconnect:
            return