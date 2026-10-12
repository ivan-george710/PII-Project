"""Static single-manager report/decision service. Never accepts full documents."""
from datetime import datetime, timezone
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Literal
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

class Part(BaseModel):
    model_config=ConfigDict(extra='forbid')
    finding_id:str=Field(max_length=80)
    category:str=Field(max_length=80)
    original:str=Field(default='',max_length=240)
    redacted:str|None=Field(default=None,max_length=240)
    original_image:str|None=Field(default=None,max_length=120000,pattern=r'^data:image/png;base64,[A-Za-z0-9+/=]+$')
    redacted_image:str|None=Field(default=None,max_length=120000,pattern=r'^data:image/png;base64,[A-Za-z0-9+/=]+$')
    truncated:bool=False

class Report(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str=Field(pattern=r'^[a-f0-9]{32}$')
    filename:str=Field(min_length=1,max_length=255)
    revision:int=Field(ge=0,strict=True)
    artifact_sha256:str|None=Field(default=None,pattern=r'^[a-f0-9]{64}$')
    ready:bool
    parts:list[Part]=Field(default_factory=list,max_length=500)
    counts:dict[str,int]=Field(default_factory=dict,max_length=100)

class Decision(BaseModel):
    model_config=ConfigDict(extra='forbid')
    revision:int=Field(ge=0,strict=True)
    artifact_sha256:str|None=Field(default=None,pattern=r'^[a-f0-9]{64}$')
    action:Literal['approved','denied']

class CustomRule(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str|None=Field(default=None,max_length=80)
    name:str=Field(min_length=1,max_length=120)
    pattern:str=Field(min_length=1,max_length=500)
    entity_type:str=Field(default='CUSTOM_BLOCKED',max_length=80)
    action:Literal['redact','block']=Field(default='redact')
    is_regex:bool=Field(default=False)
    created_at:str|None=Field(default=None)

class Store:
    def __init__(self,path=None):
        self.url=os.getenv('DATABASE_URL','') if path is None else ''
        self.path=str(path or os.getenv('MANAGER_DB_PATH','.manager-demo.sqlite'))
        self.lock=RLock()
    @contextmanager
    def connection(self):
        if self.url.startswith(('postgresql://','postgres://')):
            import psycopg
            from psycopg.rows import dict_row
            connection=psycopg.connect(self.url,row_factory=dict_row)
            try:yield connection
            finally:connection.close()
            return
        if os.getenv('VERCEL'):raise HTTPException(503,'Manager database is not configured.')
        connection=sqlite3.connect(self.path);connection.row_factory=sqlite3.Row
        try:yield connection
        finally:connection.close()
    def execute(self,connection,query,args=()):
        return connection.execute(query.replace('?', '%s') if self.url.startswith(('postgresql://','postgres://')) else query,args)
    def initialize(self,connection):
        connection.execute('CREATE TABLE IF NOT EXISTS manager_reviews (id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL, submitted_at TEXT NOT NULL, decided_at TEXT)')
        connection.execute('CREATE TABLE IF NOT EXISTS custom_rules (id TEXT PRIMARY KEY, name TEXT NOT NULL, pattern TEXT NOT NULL, entity_type TEXT NOT NULL, action TEXT NOT NULL, is_regex INTEGER NOT NULL, created_at TEXT NOT NULL)')
        try:
            cur = connection.execute('SELECT COUNT(*) FROM custom_rules')
            row = cur.fetchone()
            count = row[0] if row else 0
            if count == 0:
                defaults = [
                    ('cs-rule-1', 'Cadence Financial Group', 'Cadence Financial Group', 'CUSTOM_BLOCKED', 'redact', 0, datetime.now(timezone.utc).isoformat()),
                    ('cs-rule-2', 'OneTrust TPRM Solution', 'OneTrust TPRM', 'CUSTOM_BLOCKED', 'redact', 0, datetime.now(timezone.utc).isoformat()),
                    ('cs-rule-3', 'Optiv Security Partner', 'Optiv', 'CUSTOM_BLOCKED', 'redact', 0, datetime.now(timezone.utc).isoformat()),
                    ('cs-rule-4', 'Cadence TPRM Training', 'Cadence TPRM Training', 'CUSTOM_BLOCKED', 'redact', 0, datetime.now(timezone.utc).isoformat()),
                    ('cs-rule-5', 'Risk Management Policy', 'Cadence Group Risk Management Policy', 'CUSTOM_BLOCKED', 'redact', 0, datetime.now(timezone.utc).isoformat()),
                ]
                connection.executemany('INSERT INTO custom_rules (id, name, pattern, entity_type, action, is_regex, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)', defaults)
                connection.commit()
        except Exception:
            pass
    def list_rules(self):
        with self.lock,self.connection() as connection:
            self.initialize(connection)
            rows=self.execute(connection,'SELECT * FROM custom_rules ORDER BY created_at DESC').fetchall()
            return [{'id':r['id'],'name':r['name'],'pattern':r['pattern'],'entity_type':r['entity_type'],'action':r['action'],'is_regex':bool(r['is_regex']),'created_at':r['created_at']} for r in rows]
    def add_rule(self,body:CustomRule):
        from uuid import uuid4
        rule_id=body.id or uuid4().hex
        created_at=body.created_at or datetime.now(timezone.utc).isoformat()
        with self.lock,self.connection() as connection:
            self.initialize(connection)
            self.execute(connection,'INSERT INTO custom_rules (id,name,pattern,entity_type,action,is_regex,created_at) VALUES (?,?,?,?,?,?,?)',(rule_id,body.name,body.pattern,body.entity_type,body.action,1 if body.is_regex else 0,created_at))
            connection.commit()
            return {'id':rule_id,'name':body.name,'pattern':body.pattern,'entity_type':body.entity_type,'action':body.action,'is_regex':body.is_regex,'created_at':created_at}
    def delete_rule(self,rule_id:str):
        with self.lock,self.connection() as connection:
            self.initialize(connection)
            self.execute(connection,'DELETE FROM custom_rules WHERE id=?',(rule_id,))
            connection.commit()
            return {'status':'deleted','id':rule_id}
    def upsert(self,body):
        payload=body.model_dump_json()
        if len(payload.encode())>2*1024*1024:raise HTTPException(413,'The affected-content report is too large.')
        with self.lock,self.connection() as connection:
            self.initialize(connection)
            row=self.execute(connection,'SELECT * FROM manager_reviews WHERE id=?',(body.id,)).fetchone()
            if row:
                prior=Report.model_validate_json(row['payload'])
                if body.revision<prior.revision:raise HTTPException(409,'A newer revision is already under review.')
                if body.revision==prior.revision:
                    if payload!=row['payload']:raise HTTPException(409,'The same revision cannot change its contents.')
                    return self.view(row,True)
                updated=self.execute(connection,"UPDATE manager_reviews SET payload=?,status='pending',decided_at=NULL WHERE id=? AND payload=?",(payload,body.id,row['payload']))
                if updated.rowcount!=1:raise HTTPException(409,'The submission changed. Retry the latest revision.')
            else:
                self.execute(connection,"INSERT INTO manager_reviews (id,payload,status,submitted_at) VALUES (?,?,'pending',?)",(body.id,payload,datetime.now(timezone.utc).isoformat()))
            connection.commit()
            return self.get(body.id,connection)
    def view(self,row,details):
        payload=json.loads(row['payload'])
        if not details:payload.pop('parts',None)
        return {**payload,'status':row['status'],'submitted_at':row['submitted_at'],'decided_at':row['decided_at']}
    def get(self,identifier,connection=None):
        if connection is None:
            with self.lock,self.connection() as connection:
                self.initialize(connection);return self.get(identifier,connection)
        row=self.execute(connection,'SELECT * FROM manager_reviews WHERE id=?',(identifier,)).fetchone()
        if not row:raise HTTPException(404,'Submission not found.')
        return self.view(row,True)
    def list(self):
        with self.lock,self.connection() as connection:
            self.initialize(connection)
            return [self.view(row,False) for row in self.execute(connection,'SELECT * FROM manager_reviews ORDER BY submitted_at DESC LIMIT 100').fetchall()]
    def decide(self,identifier,body):
        with self.lock,self.connection() as connection:
            self.initialize(connection)
            row=self.execute(connection,'SELECT * FROM manager_reviews WHERE id=?',(identifier,)).fetchone()
            if not row:raise HTTPException(404,'Submission not found.')
            report=Report.model_validate_json(row['payload'])
            if report.revision!=body.revision or report.artifact_sha256!=body.artifact_sha256:raise HTTPException(409,'The result changed. Open the latest submission.')
            if body.action=='approved' and (not report.ready or not report.artifact_sha256):raise HTTPException(409,'Resolve local review and verification before approving.')
            updated=self.execute(connection,'UPDATE manager_reviews SET status=?,decided_at=? WHERE id=? AND payload=?',(body.action,datetime.now(timezone.utc).isoformat(),identifier,row['payload']))
            if updated.rowcount!=1:raise HTTPException(409,'The submission changed. Open its latest revision.')
            connection.commit()
            return self.get(identifier,connection)

def create_app(path=None):
    app=FastAPI(title='PII Guard manager',docs_url=None,redoc_url=None,openapi_url=None)
    store=Store(path);app.state.store=store
    @app.middleware('http')
    async def boundary(request:Request,next):
        if request.method in {'POST','PATCH','DELETE','PUT'}:
            if request.headers.get('x-cadence-local')!='1':return __import__('starlette.responses',fromlist=['JSONResponse']).JSONResponse({'detail':'Use the manager application.'},status_code=403)
            try:size=int(request.headers.get('content-length','0'))
            except ValueError:return JSONResponse({'detail':'Invalid request size.'},status_code=400)
            if size<0 or size>2*1024*1024:return JSONResponse({'detail':'Report too large.'},status_code=413)
        response=await next(request);response.headers['Cache-Control']='no-store';response.headers['X-Content-Type-Options']='nosniff';return response
    @app.get('/api/health')
    def health():return {'status':'ok','mode':'manager','commit':os.getenv('VERCEL_GIT_COMMIT_SHA')}
    @app.post('/api/manager/reports')
    def publish(body:Report):return store.upsert(body)
    @app.get('/api/manager/reports')
    def reports():return {'items':store.list()}
    @app.get('/api/manager/reports/{identifier}')
    def detail(identifier:str):return store.get(identifier)
    @app.post('/api/manager/reports/{identifier}/decision')
    def decide(identifier:str,body:Decision):return store.decide(identifier,body)
    @app.get('/api/manager/rules')
    def get_rules():return {'items':store.list_rules()}
    @app.post('/api/manager/rules')
    def create_rule(body:CustomRule):return store.add_rule(body)
    @app.delete('/api/manager/rules/{rule_id}')
    def remove_rule(rule_id:str):return store.delete_rule(rule_id)
    static=Path(__file__).resolve().parents[1]/'app/web/static'
    if static.is_dir() and not os.getenv('VERCEL'):
        app.mount('/assets',StaticFiles(directory=static),name='assets')
        @app.get('/manager')
        def page():return FileResponse(static/'index.html')
        @app.get('/')
        def root():
            from fastapi.responses import RedirectResponse
            return RedirectResponse('/manager', status_code=307)
    return app
app=create_app()
