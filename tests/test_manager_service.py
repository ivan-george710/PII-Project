"""Revision, readiness and affected-content-only contracts for the remote manager."""
from hashlib import sha256
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from manager.server import create_app
from app.web.manager_client import ManagerClient

HEADERS={'X-Cadence-Local':'1'}
ID='a'*32
HASH='b'*64

def report(**changes):
    return {'id':ID,'filename':'sample.pdf','revision':0,'artifact_sha256':HASH,'ready':True,'parts':[{'finding_id':'person-1','category':'PERSON','original':'Jane Smith','redacted':'[REDACTED]'}],'counts':{},**changes}

def test_decisions_are_revision_bound_and_idempotent(tmp_path):
    client=TestClient(create_app(tmp_path/'manager.sqlite'))
    assert client.post('/api/manager/reports',json=report(),headers=HEADERS).status_code==200
    decision={'revision':0,'artifact_sha256':HASH,'action':'approved'}
    assert client.post(f'/api/manager/reports/{ID}/decision',json=decision,headers=HEADERS).json()['status']=='approved'
    assert client.post('/api/manager/reports',json=report(),headers=HEADERS).json()['status']=='approved'
    assert 'parts' not in client.get('/api/manager/reports').json()['items'][0]
    assert client.post('/api/manager/reports',json=report(revision=1),headers=HEADERS).json()['status']=='pending'
    assert client.post(f'/api/manager/reports/{ID}/decision',json=decision,headers=HEADERS).status_code==409
    assert client.post('/api/manager/reports',json=report(),headers=HEADERS).status_code==409

def test_rejects_full_content_and_unready_approval(tmp_path):
    client=TestClient(create_app(tmp_path/'manager.sqlite'))
    assert client.post('/api/manager/reports',json=report(full_text='private'),headers=HEADERS).status_code==422
    assert client.post('/api/manager/reports',json=report(),headers={}).status_code==403
    assert client.post('/api/manager/reports',json=report(ready=False,artifact_sha256=None),headers=HEADERS).status_code==200
    decision={'revision':0,'artifact_sha256':None,'action':'approved'}
    assert client.post(f'/api/manager/reports/{ID}/decision',json=decision,headers=HEADERS).status_code==409
    decision['action']='denied'
    assert client.post(f'/api/manager/reports/{ID}/decision',json=decision,headers=HEADERS).json()['status']=='denied'

def test_same_revision_cannot_replace_artifact(tmp_path):
    client=TestClient(create_app(tmp_path/'manager.sqlite'))
    client.post('/api/manager/reports',json=report(),headers=HEADERS)
    assert client.post('/api/manager/reports',json=report(artifact_sha256='c'*64),headers=HEADERS).status_code==409

def test_download_gate_checks_exact_current_bytes(tmp_path):
    path=tmp_path/'result.pdf';path.write_bytes(b'verified result')
    client=ManagerClient('http://127.0.0.1:8766')
    decision={'revision':2,'artifact_sha256':sha256(path.read_bytes()).hexdigest(),'status':'approved','ready':True}
    client.status=lambda identifier:decision
    client.require_approved(ID,2,path)
    decision['status']='denied'
    with pytest.raises(HTTPException) as error:client.require_approved(ID,2,path)
    assert error.value.status_code==403
    decision['status']='approved';path.write_bytes(b'changed result')
    with pytest.raises(HTTPException) as error:client.require_approved(ID,2,path)
    assert error.value.status_code==409

@pytest.mark.parametrize('url',['http://remote.test','https://user:pass@remote.test','https://remote.test/path'])
def test_manager_transport_requires_safe_origin(url):
    with pytest.raises(ValueError):ManagerClient(url)
