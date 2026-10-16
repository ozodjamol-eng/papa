"""Private API + owner web console; only read-only/locally reversible actions execute."""
from __future__ import annotations
import asyncio, hmac, json, os, secrets, time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from .core import Store, SAFE_AGENT, SAFE_SERVER, RESTRICTED, RUNNER, POLICY, safe_server_execute

ROOT=Path(__file__).resolve().parent.parent

class Settings:
    def __init__(self, db=None, state_dir=None, owner_password_hash=None, ai_token=None,
                 agents=None, secure_cookies=True, probes_enabled=False, run_worker=True):
        self.db=Path(db or os.getenv('NEXUS_CONTROL_DB',str(ROOT/'var'/'control.sqlite3')))
        self.state_dir=Path(state_dir or os.getenv('NEXUS_CONTROL_STATE',str(ROOT/'var'/'state')))
        self.owner_password_hash=owner_password_hash or os.getenv('NEXUS_OWNER_PASSWORD_HASH','')
        self.ai_token=ai_token if ai_token is not None else os.getenv('NEXUS_AI_TOKEN','')
        if self.ai_token and len(self.ai_token)<32:raise RuntimeError('ai_token_too_short')
        if agents is None:
            try: agents=json.loads(os.getenv('NEXUS_AGENT_TOKENS_JSON','{}'))
            except ValueError: raise RuntimeError('invalid_agent_tokens_config')
        self.agents=agents
        self.secure_cookies=secure_cookies
        self.probes_enabled=probes_enabled
        self.run_worker=run_worker
        if not self.owner_password_hash:raise RuntimeError('configure_NEXUS_OWNER_PASSWORD_HASH_before_start')
        if not isinstance(self.agents,dict) or any(not isinstance(k,str) or not isinstance(v,str) or len(v)<24 for k,v in self.agents.items()):
            raise RuntimeError('invalid_agent_credentials')

class Login(BaseModel):
    password:str=Field(min_length=1,max_length=256)
class CreateTask(BaseModel):
    operation:str=Field(min_length=1,max_length=80)
    target:str='cloud'
    payload:dict={}
    idempotency_key:str|None=None
class Approve(BaseModel):
    confirmation:str
class AgentHello(BaseModel):
    platform:str=Field(max_length=50)
    hostname:str=Field(max_length=90)
    details:dict={}
class AgentResult(BaseModel):
    task_id:str
    ok:bool
    result:dict={}


def create_app(config:Settings|None=None):
    cfg=config or Settings()
    store=Store(cfg.db,cfg.state_dir)
    hasher=PasswordHasher()
    auth_failures=defaultdict(deque)

    def run_once():
        row=store.claim_server()
        if not row:return None
        try:
            result=safe_server_execute(store,row['operation'],json.loads(row['payload']),cfg.probes_enabled)
            status='succeeded'
        except Exception as exc:
            result={'error':type(exc).__name__,'message':str(exc)[:180]};status='failed'
        store.finish(row['id'],status,result)
        return {'id':row['id'],'status':status,'result':result}

    heartbeat=Path(cfg.state_dir)/'worker.heartbeat'
    def beat():
        tmp=heartbeat.with_suffix('.tmp');tmp.write_text(str(time.time()));os.replace(tmp,heartbeat)
    async def worker_loop():
        last_housekeeping=0.0
        while True:
            try:
                await asyncio.to_thread(run_once)
            except Exception:
                # Do not expose secrets in logs
                pass
            try:
                if time.monotonic()-last_housekeeping>900:
                    await asyncio.to_thread(store.housekeeping);last_housekeeping=time.monotonic()
                beat()
            except Exception:
                pass
            await asyncio.sleep(0.65)

    @asynccontextmanager
    async def lifespan(app):
        task=asyncio.create_task(worker_loop()) if cfg.run_worker else None
        try: yield
        finally:
            if task:
                task.cancel()
                try:await task
                except asyncio.CancelledError:pass

    app=FastAPI(title='NEXUS Private Control V2',docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
    app.state.store=store
    app.state.execute_once=run_once
    app.state.config=cfg

    @app.middleware('http')
    async def protections(request:Request,call_next):
        if request.url.path.startswith('/api/') and request.method not in ('GET','HEAD','OPTIONS'):
            origin=request.headers.get('origin')
            if origin:
                origin_parts=urlparse(origin)
                if origin_parts.netloc!=request.headers.get('host') or origin_parts.scheme not in ('https','http'):
                    return JSONResponse({'error':'origin_mismatch'},status_code=403)
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        return response

    def context(request:Request, mutation=False, allow_ai=False):
        cookie=request.cookies.get('nexus_session','')
        if store.session(cookie):
            if mutation and not store.verify_csrf(cookie,request.headers.get('x-csrf-token','')):
                raise HTTPException(403,'csrf_required')
            return 'owner'
        if allow_ai and cfg.ai_token:
            header=request.headers.get('authorization','')
            token=header[7:] if header.startswith('Bearer ') else ''
            if hmac.compare_digest(token,cfg.ai_token):return 'ai'
        raise HTTPException(401,'authentication_required')

    def device_auth(request:Request):
        device_id=request.headers.get('x-device-id','')
        supplied=request.headers.get('authorization','')
        token=supplied[7:] if supplied.startswith('Bearer ') else ''
        expected=cfg.agents.get(device_id)
        if not expected or not token or not hmac.compare_digest(token,expected):raise HTTPException(401,'agent_auth_required')
        return device_id

    @app.get('/')
    def dashboard():return FileResponse(ROOT/'static'/'index.html',media_type='text/html')
    @app.get('/app.js')
    def js():return FileResponse(ROOT/'static'/'app.js',media_type='text/javascript')
    @app.get('/style.css')
    def css():return FileResponse(ROOT/'static'/'style.css',media_type='text/css')

    @app.post('/api/login')
    def login(body:Login,request:Request):
        address=request.client.host if request.client else 'unknown'
        now=time.monotonic();failures=auth_failures[address]
        while failures and failures[0]<now-900:failures.popleft()
        if len(failures)>=5:raise HTTPException(429,'temporarily_locked')
        try:
            hasher.verify(cfg.owner_password_hash,body.password)
        except (VerifyMismatchError,VerificationError):
            failures.append(now)
            raise HTTPException(401,'invalid_credentials')
        failures.clear()
        token,csrf=store.new_session()
        resp=JSONResponse({'ok':True,'csrf':csrf})
        resp.set_cookie('nexus_session',token,httponly=True,secure=cfg.secure_cookies,
                        samesite='strict',max_age=8*3600,path='/')
        resp.set_cookie('nexus_csrf',csrf,httponly=False,secure=cfg.secure_cookies,
                        samesite='strict',max_age=8*3600,path='/')
        return resp
    @app.get('/api/me')
    def me(request:Request):
        role=context(request,allow_ai=True)
        return {'role':role,'mode':'autonomous_safe','csrf_required_for_mutations':role=='owner'}
    @app.post('/api/logout')
    def logout(request:Request):
        context(request,mutation=True)
        store.logout(request.cookies.get('nexus_session',''))
        resp=JSONResponse({'ok':True});resp.delete_cookie('nexus_session',path='/');resp.delete_cookie('nexus_csrf',path='/');return resp
    @app.get('/api/status')
    def status(request:Request):
        role=context(request,allow_ai=True)
        return {'gateway':'online','mode':POLICY['mode'],'role':role,'queue':store.counts(),
                'devices':[{'id':x['id'],'platform':x['platform'],'hostname':x['hostname'],
                            'online':x['online'],'last_seen':x['last_seen']} for x in store.devices()],
                'production_connected':cfg.probes_enabled,
                'publisher_connected':False,'capabilities':{'cloud':sorted(SAFE_SERVER),'agent':sorted(SAFE_AGENT),'frankfurt':sorted(RUNNER)}}
    @app.get('/api/tasks')
    def tasks(request:Request):
        context(request,allow_ai=True)
        return {'tasks':store.tasks()}
    @app.post('/api/tasks')
    def submit(request:Request,body:CreateTask):
        actor=context(request,mutation=True,allow_ai=True)
        if actor=='ai' and body.operation in RESTRICTED:raise HTTPException(403,'ai_cannot_request_critical_actions')
        try:return store.create(actor,body.operation,body.payload,body.target,body.idempotency_key)
        except ValueError as e:raise HTTPException(422,str(e))
    @app.get('/api/tasks/{task_id}')
    def task_one(task_id:str,request:Request):
        context(request,allow_ai=True)
        if not task_id.isalnum() or len(task_id)>40:raise HTTPException(422,'bad_id')
        row=store.get(task_id)
        if not row:raise HTTPException(404,'task_not_found')
        return {k:row[k] for k in ('id','operation','target','status','payload','result','requested_by','created_at','updated_at')}
    @app.post('/api/tasks/{task_id}/approve')
    def approve(task_id:str,body:Approve,request:Request):
        if context(request,mutation=True)!='owner':raise HTTPException(403,'owner_only')
        try:return store.approve(task_id,'owner',body.confirmation)
        except (ValueError,PermissionError) as e:raise HTTPException(422,str(e))
    @app.get('/api/audit')
    def audit(request:Request):
        context(request,allow_ai=True)
        return {'events':store.audit()}
    @app.get('/api/devices')
    def devices(request:Request):
        context(request,allow_ai=True)
        return {'devices':[{'id':x['id'],'hostname':x['hostname'],'platform':x['platform'],
                            'online':x['online'],'last_seen':x['last_seen'],'details':json.loads(x['details'])}
                           for x in store.devices()]}

    @app.get('/api/razvedka')
    def razvedka(request:Request):
        context(request,allow_ai=True)
        p=Path(os.getenv('NEXUS_RAZVEDKA_REPORT','/var/lib/papa-razvedka-pub/latest.json'))
        try: data=json.loads(p.read_text(encoding='utf-8'))
        except FileNotFoundError: raise HTTPException(404,'no_report_yet')
        except (OSError,ValueError): raise HTTPException(503,'report_unreadable')
        if not isinstance(data,dict): raise HTTPException(503,'report_unreadable')
        data['age_hours']=round((time.time()-p.stat().st_mtime)/3600,1)
        return data

    @app.get('/api/voronka')
    def voronka(request:Request):
        context(request,allow_ai=True)
        p=Path(os.getenv('NEXUS_VORONKA_STATS','/var/lib/papa-voronka-pub/stats.json'))
        try: data=json.loads(p.read_text(encoding='utf-8'))
        except FileNotFoundError: raise HTTPException(404,'no_stats_yet')
        except (OSError,ValueError): raise HTTPException(503,'stats_unreadable')
        if not isinstance(data,dict): raise HTTPException(503,'stats_unreadable')
        data['age_minutes']=round((time.time()-p.stat().st_mtime)/60,1)
        return data

    @app.post('/api/agent/hello')
    def hello(request:Request,body:AgentHello):
        device_id=device_auth(request)
        store.seen(device_id,body.platform,body.hostname,body.details)
        return {'ok':True,'device_id':device_id,'allowed':sorted(SAFE_AGENT)}
    @app.post('/api/agent/next')
    def next_task(request:Request):
        device_id=device_auth(request)
        return {'task':store.next_agent(device_id)}
    @app.post('/api/agent/result')
    def agent_result(request:Request,body:AgentResult):
        device_id=device_auth(request)
        try:store.agent_finish(device_id,body.task_id,body.ok,body.result)
        except ValueError as exc:raise HTTPException(409,str(exc))
        return {'ok':True}
    return app

app=None  # uvicorn uses nexus_control.run:app, with env validated before startup
