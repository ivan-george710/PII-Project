from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from app.web.server import create_app
from tools.create_phase11_fixtures import create


def test_actual_face_api_review_crop_and_saved_replay(tmp_path):
    path=create(tmp_path/'fixture')/'synthetic-face.pptx'
    app=create_app(work_dir=tmp_path/'private-app',allow_test_host=True);client=TestClient(app)
    response=client.post('/api/documents',files={'file':(path.name,path.read_bytes())},headers={'X-Cadence-Local':'1'})
    assert response.status_code==200
    state=response.json();sid=state['document_session_id'];base=f'/api/documents/{sid}'
    assert state['summary']['visual_privacy']['detected_faces']==1
    assert state['summary']['artifact']['protected_faces']==1
    assert state['summary']['artifact']['face_transformations_verified']
    assert not state['summary']['safe_for_llm']
    values=client.get(base+'/findings?entity=FACE').json();assert values['total']==1
    face=values['items'][0];assert face['kind']=='VISUAL' and face['locations']==[1,2]
    assert face['recognizer']=='YuNet' and face['protected'] and not face['corrected']
    assert face['automated_decision']=='CONFIRM'
    detail=client.get(base+'/findings/'+face['finding_id']).json()
    assert detail['candidate']=='' and detail['visual_before_url'] and detail['visual_after_url']
    before=client.get(detail['visual_before_url']);after=client.get(detail['visual_after_url'])
    assert before.status_code==after.status_code==200 and before.content!=after.content
    assert before.headers['cache-control']=='no-store'
    with Image.open(BytesIO(before.content)) as im:assert max(im.size)<=512
    text_raw=state['summary']['audit']['counts']['raw_detection_count']
    payload=dict(expected_revision=0,action='FALSE_POSITIVE',finding_id=face['finding_id'],reviewer_id='synthetic-reviewer')
    response=client.post(base+'/feedback',json=payload,headers={'X-Cadence-Local':'1'});assert response.status_code==200
    changed=response.json();assert changed['revision']==1
    assert changed['summary']['artifact']['protected_faces']==0
    assert changed['summary']['audit']['counts']['raw_detection_count']==text_raw
    assert client.get(detail['visual_after_url']).status_code==409 # stale image revision
    payload.update(expected_revision=1,action='CONFIRM_PII')
    response=client.post(base+'/feedback',json=payload,headers={'X-Cadence-Local':'1'});assert response.status_code==200
    assert response.json()['revision']==2 and response.json()['summary']['artifact']['protected_faces']==1
    saved=client.post(base+'/save',json={'expected_revision':2},headers={'X-Cadence-Local':'1'});assert saved.status_code==200
    references=client.get('/api/saved-audits').json()
    restored=client.post('/api/load-audit',json={'audit_reference':references[0]['audit_reference']},headers={'X-Cadence-Local':'1'})
    assert restored.status_code==200 and restored.json()['revision']==2
    assert restored.json()['summary']['artifact']['protected_faces']==1
    for key in ['coverage_verified','safe_for_llm','downstream_export_permitted']:assert not restored.json()['summary'][key]
    assert 'source_ref' not in str(values) and str(tmp_path) not in response.text
