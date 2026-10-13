"""Revision, readiness and affected-content-only contracts for the remote manager."""
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

def test_download_blocks_only_explicit_denial_and_allows_manager_outage():
    client=ManagerClient('http://127.0.0.1:8766')
    decision={'status':'pending','ready':False}
    client.status=lambda identifier:decision
    client.check_denial(ID)
    decision['status']='approved';client.check_denial(ID)
    decision['status']='denied'
    with pytest.raises(HTTPException) as error:client.check_denial(ID)
    assert error.value.status_code==403
    client.status=lambda identifier:(_ for _ in ()).throw(HTTPException(503,'Unavailable'))
    client.check_denial(ID)

@pytest.mark.parametrize('url',['http://remote.test','https://user:pass@remote.test','https://remote.test/path'])
def test_manager_transport_requires_safe_origin(url):
    with pytest.raises(ValueError):ManagerClient(url)

def test_rules_start_empty_and_reject_invalid_or_unimplemented_actions(tmp_path):
    client=TestClient(create_app(tmp_path/'rules.sqlite'))
    assert client.get('/api/manager/rules').json()=={'items':[]}
    body={'name':'Demo secret','pattern':'DemoOnly123!','action':'redact'}
    response=client.post('/api/manager/rules',json=body,headers=HEADERS)
    assert response.status_code==200
    assert len(client.get('/api/manager/rules').json()['items'])==1
    for changes in ({'is_regex':True,'pattern':'['},{'is_regex':True,'pattern':'.*'},{'action':'block'},{'pattern':' '},{'entity_type':'bad value'}):
        assert client.post('/api/manager/rules',json={**body,**changes},headers=HEADERS).status_code==422
    assert client.delete('/api/manager/rules/'+response.json()['id'],headers=HEADERS).status_code==200
    # Deleting the last rule must not resurrect hard-coded defaults.
    assert client.get('/api/manager/rules').json()=={'items':[]}


def test_large_affected_report_has_small_privacy_preserving_status(tmp_path):
    client=TestClient(create_app(tmp_path/'manager.sqlite'))
    parts=[{'finding_id':f'finding-{i}','category':'PERSON','original':'Jane Smith','redacted':'[PERSON]'} for i in range(1160)]
    assert client.post('/api/manager/reports',json=report(parts=parts),headers=HEADERS).status_code==200
    assert len(client.get(f'/api/manager/reports/{ID}').json()['parts'])==1160
    status=client.get(f'/api/manager/reports/{ID}/status')
    assert status.status_code==200
    assert set(status.json())=={'id','revision','status','ready','artifact_sha256'}
    assert status.json()['status']=='pending'
    assert 'Jane Smith' not in status.text
