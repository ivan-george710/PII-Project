"""Send affected parts only; employee artifacts and engine execution remain local."""
from hashlib import sha256
import json
import os
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from urllib.error import HTTPError,URLError
from fastapi import HTTPException

class ManagerClient:
    def __init__(self,url=None,client=None):
        self.client=client
        if client is not None:
            self.url=(url or 'http://127.0.0.1:8766').rstrip('/')
            return
        self.url=(url or os.getenv('REMOTE_MANAGER_URL','http://127.0.0.1:8766')).rstrip('/')
        parsed=urlsplit(self.url)
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path or not parsed.hostname or (parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in {'localhost','127.0.0.1','::1'})):
            raise ValueError('Manager URL must be an HTTPS origin or a local development origin.')
    def call(self,path,body=None):
        if self.client is not None:
            payload=body
            if body is not None and len(json.dumps(body).encode())>2*1024*1024:
                raise HTTPException(413,'Manager report is too large. Download stays blocked.')
            try:
                if body is not None:
                    response=self.client.post('/api/manager'+path,json=payload,headers={'X-Cadence-Local':'1'})
                else:
                    response=self.client.get('/api/manager'+path,headers={'X-Cadence-Local':'1'})
                if response.status_code>=400:
                    detail=response.json().get('detail','Manager error') if response.headers.get('content-type','').startswith('application/json') else response.text
                    raise HTTPException(response.status_code,detail)
                return response.json()
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(503,'Manager service is unavailable. Download stays blocked.') from None
        payload=json.dumps(body).encode() if body is not None else None
        if payload and len(payload)>2*1024*1024:raise HTTPException(413,'Manager report is too large. Download stays blocked.')
        try:
            with urlopen(Request(self.url+'/api/manager'+path,data=payload,headers={'Content-Type':'application/json','X-Cadence-Local':'1'}),timeout=10) as response:return json.loads(response.read(3*1024*1024))
        except (HTTPError,URLError,TimeoutError,ValueError):raise HTTPException(503,'Manager service is unavailable. Download stays blocked.') from None
    def publish(self,body):return self.call('/reports',body)
    def status(self,identifier):return self.call('/reports/'+identifier)
    def get_rules(self):
        try:
            res = self.call('/rules')
            return res.get('items', []) if isinstance(res, dict) else []
        except Exception:
            return []
    def require_approved(self,identifier,revision,path):
        decision=self.status(identifier)
        if decision['revision']!=revision or decision['artifact_sha256']!=sha256(path.read_bytes()).hexdigest():raise HTTPException(409,'The redacted result changed and needs a new approval.')
        if decision['status']!='approved':raise HTTPException(403,'Manager approval is required to download this result.')
        if not decision['ready']:raise HTTPException(409,'The engine has not verified this result.')
