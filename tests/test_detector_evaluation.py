"""Independent scoring, context and private curation regression tests."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.engines.pii_detection import PIIDetectionEngine
from app.engines.pii_detection.models import DetectedPII, PIIDetectionResult
from app.engines.pii_detection.validation import validate_detection, DETECTOR_POLICY_VERSION
from app.engines.extraction.models import ExtractionResult, ExtractedPage
from app.engines.audit import AuditEngine, ReviewerFeedback
from app.engines.audit.feedback_export import export_feedback
from app.engines.redaction import RedactionEngine
from tools.evaluate_detector import metrics, summarize
from tools.build_detector_dataset import build


def check(value, entity, context=None, confidence=.85):
    d=DetectedPII(entity,value,0,len(value),confidence,'pattern','Synthetic',1)
    return validate_detection(d,context or value)[0].value


@pytest.mark.parametrize('value,entity,context,expected',[
    ('EMP-12345','EMPLOYEE_ID',None,'CONFIRM'),
    ('EMP-1234','EMPLOYEE_ID',None,'REJECT'),
    ('EMP-１２３４５','EMPLOYEE_ID',None,'REJECT'),
    ('EMP-12345','EMPLOYEE_ID','EMP-12345-extra','AMBIGUOUS'),
    ('ada@example.com','EMAIL_ADDRESS',None,'CONFIRM'),
    ('ada..example@example.com','EMAIL_ADDRESS',None,'REJECT'),
    ('ada@','EMAIL_ADDRESS',None,'AMBIGUOUS'),
    ('+1 (212) 555-0101','PHONE_NUMBER',None,'CONFIRM'),
    ('2125550101','PHONE_NUMBER','Revenue amount: 2125550101 dollars','REJECT'),
    ('2125550101','PHONE_NUMBER','Project code ZY-2125550101','REJECT'),
    ('123','PHONE_NUMBER',None,'AMBIGUOUS'),
    ('John Smith','PERSON',None,'CONFIRM'),
    ('Risk Management','PERSON',None,'REJECT'),
    ('Operations Team','PERSON',None,'REJECT'),
    ('Smith Risk Committee','PERSON',None,'REJECT'),
    ('Alder Holdings Limited','PERSON',None,'REJECT'),
    ('Brightwell','PERSON',None,'AMBIGUOUS'),
    ('JohnSmith','PERSON',None,'AMBIGUOUS'),
    ('Blue Horizon','PERSON',None,'CONFIRM'),  # Two words alone remain ambiguous in meaning.
    ('73001234','US_BANK_NUMBER','Bank account number: 73001234','AMBIGUOUS'),
    ('73001234','US_DRIVER_LICENSE',None,'AMBIGUOUS'),
])
def test_targeted_validation(value,entity,context,expected):
    assert check(value,entity,context)==expected


def test_low_confidence_person_and_no_remote_rejection():
    assert check('John Smith','PERSON',confidence=.2)=='AMBIGUOUS'
    assert check('2125550101','PHONE_NUMBER','Revenue amount: 42 dollars. Telephone: 2125550101')=='CONFIRM'
    assert check('John Smith','PERSON','John Smith works with the Operations Team.')=='CONFIRM'


def test_duplicate_context_exact_occurrence_and_accounting():
    text='Revenue amount: 2125550101 dollars. Telephone: 2125550101'
    positions=[text.index('2125550101'),text.rindex('2125550101')]
    candidates=[SimpleNamespace(start=s,end=s+10,entity_type='PHONE_NUMBER',score=.4,
                               recognition_metadata={'recognizer_name':'Synthetic'}) for s in positions]
    candidates.append(deepcopy(candidates[1]))
    analyzer=SimpleNamespace(analyze=lambda **kwargs:candidates)
    extraction=ExtractionResult(Path('synthetic.txt'),'synthetic.txt','text',[ExtractedPage(1,text,'text')])
    result=PIIDetectionEngine(analyzer=analyzer).detect(extraction)
    assert len(result.rejected)==1 and len(result.detections)==2
    assert result.raw_candidate_count==result.disposition_count==3
    redaction=RedactionEngine().redact(extraction,result)
    assert redaction.applied_redaction_count==1
    assert '2125550101 dollars' in redaction.full_text
    assert not redaction.safe_for_llm


def test_metrics_exact_entity_review_and_duplicates():
    g={('a',0,5,'PERSON'),('b',0,3,'EMPLOYEE_ID')}
    c={('a',0,5,'PERSON'),('x',0,4,'PHONE_NUMBER')}
    r={('b',0,3,'EMPLOYEE_ID'),('z',0,2,'PERSON')}
    m=metrics(g,c,r)
    assert (m['tp'],m['fp'],m['fn'])==(1,1,1)
    assert (m['precision'],m['recall'],m['f1'])==(.5,.5,.5)
    assert m['potential_recall']==1 and m['review_false_spans']==1
    assert metrics(g,{('a',0,5,'EMAIL_ADDRESS')},set())['tp']==0
    assert metrics(set(),set(),set())['f1']==0
    row=dict(id='a',category='synthetic',expected=[dict(start=0,end=5,entity_type='PERSON')],
        candidates=[dict(start=0,end=5,entity_type='PERSON',decision='CONFIRM')]*2)
    s=summarize([row])
    assert s['tp']==1 and s['duplicate_candidates']==1 and s['raw_candidates']==2


def test_dataset_reproducible_separated_version():
    data=build()
    stored=json.loads((Path(__file__).parent/'data/detector_evaluation.json').read_text())
    assert data==stored and len(data['cases'])==420
    dev={c['id'] for c in data['cases'] if c['split']=='development'}
    held={c['id'] for c in data['cases'] if c['split']=='heldout'}
    assert not dev & held and len(dev)==299 and len(held)==121
    assert DETECTOR_POLICY_VERSION=='1.1'
    for c in data['cases']:
        for span in c['expected']+c['non_pii']:
            assert 0<=span['start']<span['end']<=len(c['text'])


def reviewed_audit():
    text='Owner: Brightwell; ada@example.com'
    ext=ExtractionResult(Path('synthetic.txt'),'synthetic.txt','text',[ExtractedPage(1,text,'text')])
    d=DetectedPII('PERSON','Brightwell',7,17,.85,'nlp','Synthetic',1,
                 validation_decision='AMBIGUOUS',validation_reason='fixture',final_decision='REVIEW')
    det=PIIDetectionResult(ext.source_path,ext.filename,[],[],[d],1,[1])
    engine=AuditEngine()
    audit=engine.create_audit(ext,det,RedactionEngine().redact(ext,det))
    return engine.apply_feedback(audit,ReviewerFeedback('CONFIRM_PII','private-reviewer',audit.records[0].detection_id,
                                                       reason='private sensitive reason'))


def test_private_export_opt_in_sanitization_and_no_mutation(tmp_path):
    audit=reviewed_audit(); original=deepcopy(audit)
    path=export_feedback(audit,directory=tmp_path/'private',detector_version='1.0',source_category='synthetic')
    content=path.read_text(); payload=json.loads(content)
    assert 'Brightwell' not in content and 'ada@' not in content
    assert 'private-reviewer' not in content and 'sensitive reason' not in content
    assert 'synthetic.txt' not in content and audit.document_id not in content
    row=payload['examples'][0]
    assert row['automated_decision']=='REVIEW' and row['reviewer_decision']=='CONFIRM'
    assert row['detector_policy_version']=='1.0' and row['recognizer']=='Synthetic'
    assert (path.parent/'.gitignore').read_text()=='*\n!.gitignore\n'
    assert audit==original
    with pytest.raises(ValueError): export_feedback(audit,directory=path.parent)
    contextual=export_feedback(audit,directory=tmp_path/'context',include_context=True)
    row=json.loads(contextual.read_text())['examples'][0]
    assert 'Brightwell' in row['context'] and len(row['context'])<=400
    assert row['detector_policy_version']=='unknown-legacy'


def test_export_public_path_rejected(tmp_path):
    from app.engines.audit import AuditStorageError
    with pytest.raises(AuditStorageError):
        export_feedback(reviewed_audit(),directory=tmp_path/'public')
