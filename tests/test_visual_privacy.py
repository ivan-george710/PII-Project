"""Actual local YuNet + serialized artifact verification on synthetic faces."""
from copy import deepcopy
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile
import json
import numpy as np
import pytest
from PIL import Image,ImageFilter
import pymupdf as fitz
from app.engines.visual_detection import FaceDetector,FaceDetectionError,VisualInspectionEngine
from app.engines.visual_detection.images import decode,encode,blur,pixel_hash,pixel_box
from app.engines.visual_detection.detector import same_face
from app.engines.visual_detection.models import FaceDetection,VisualInspection
from app.engines.extraction.models import ExtractionResult,ExtractedPage,OCRTextBlock,PDFSourceMap
from app.engines.extraction.office import source_hash
from app.engines.extraction.docx import extract_docx
from app.engines.extraction.pptx import extract_pptx
from app.engines.extraction.pdf import extract_text_pdf
from app.engines.audit import AuditEngine,ReviewerFeedback,AuditValidationError
from app.engines.redaction import RedactionEngine
from app.engines.redaction.document_artifacts import DocumentArtifactEngine
from app.engines.pii_detection import PIIDetectionEngine
from app.engines.pii_detection.models import PIIDetectionResult,DetectedPII
from app.pipeline import DocumentPipeline
from tools.create_phase11_fixtures import create

FACE=Path(__file__).parent/'fixtures/visual/synthetic-face.png'


@pytest.fixture(scope='module')
def detector():return FaceDetector()


def employee_detection(extraction):
    detections=[]
    for p in extraction.pages:
        start=p.text.find('EMP-00001')
        if start>=0:detections.append(DetectedPII('EMPLOYEE_ID','EMP-00001',start,start+9,.95,'pattern','Synthetic',p.page_number,
            validation_decision='CONFIRM',final_decision='CONFIRM'))
    return PIIDetectionResult(extraction.source_path,extraction.filename,detections,[],[],len(detections),[p.page_number for p in extraction.pages])


def scan_extraction(path):
    text='Employee EMP-00001'
    return ExtractionResult(path,path.name,'pdf',[ExtractedPage(1,text,'ocr',[
        OCRTextBlock(text,.99,[[15,535],[400,535],[400,578],[15,578]])])],
        pdf_source=PDFSourceMap(source_hash(path),{'1':72}))


def test_one_face_normalized_and_rotated(detector):
    data=FACE.read_bytes();faces=detector.detect(data)
    assert len(faces)==1 and faces[0][1]>=.85
    for angle in (90,180,270):
        with decode(data) as im:rotated=encode(im.rotate(angle,expand=True))
        assert any(s>=.85 for _,s in detector.detect(rotated))
    for box,score in faces:
        x,y,w,h=box;assert 0<=x<x+w<=1 and 0<=y<y+h<=1 and 0<=score<=1


def test_multiple_faces_and_large_tiled_image(detector):
    with decode(FACE.read_bytes()) as im:
        canvas=Image.new('RGB',(1200,700),'white');canvas.paste(im,(20,20));canvas.paste(im,(650,100))
        faces=detector.detect(encode(canvas));canvas.close()
    assert sum(score>=.85 for _,score in faces)>=2
    assert same_face([.2,.2,.3,.3],[.21,.2,.3,.3])
    assert not same_face([.1,.1,.2,.2],[.7,.7,.2,.2])
    # The single face seen in full-frame and overlapping tile passes is deduped.
    with decode(FACE.read_bytes()) as im:
        canvas=Image.new('RGB',(800,800),'white');canvas.paste(im,(150,100));faces=detector.detect(encode(canvas))
    high=[box for box,score in faces if score>=.85]
    assert high and all(not same_face(a,b) for i,a in enumerate(high) for b in high[i+1:])


def test_no_face_corrupt_unsupported_and_model_failure(detector,tmp_path):
    image=Image.new('RGB',(320,320),'white');assert detector.detect(encode(image))==[]
    for data in (b'not an image',b'<svg></svg>'):
        with pytest.raises(FaceDetectionError,match='could not complete'):detector.detect(data)
    gif=BytesIO();image.save(gif,format='GIF')
    with pytest.raises(FaceDetectionError):detector.detect(gif.getvalue())
    bad=tmp_path/'model.onnx';bad.write_bytes(b'fake weights')
    for path in (bad,tmp_path/'missing.onnx'):
        with pytest.raises(FaceDetectionError,match='unavailable or untrusted'):FaceDetector(path)


def test_blur_strength_and_metadata_orientation_removal(detector):
    box,score=detector.detect(FACE.read_bytes())[0]
    face=FaceDetection('V000001','I000001',box,score,'png',1,[1],'fixture')
    with decode(FACE.read_bytes()) as im:
        changed,evidence=blur(im,[face]);pixels=pixel_box(box,*im.size)
        assert pixel_hash(im.crop(pixels))!=pixel_hash(changed.crop(pixels))
        before=np.asarray(im.crop(pixels),dtype=float);after=np.asarray(changed.crop(pixels),dtype=float)
        gradient=lambda a:np.abs(np.diff(a,axis=0)).mean()+np.abs(np.diff(a,axis=1)).mean()
        assert gradient(after)<gradient(before)*.25
        assert evidence[0]['radius']>=12
        # Metadata-rich orientation source is canonicalized and freshly encoded.
        exif=Image.Exif();exif[274]=6;exif[315]='PRIVATE fixture metadata'
        buf=BytesIO();im.save(buf,format='JPEG',exif=exif)
    with decode(buf.getvalue()) as canonical:
        data=encode(canonical)
    with Image.open(BytesIO(data)) as clean:
        assert not clean.getexif() and 'exif' not in clean.info and 'icc_profile' not in clean.info


@pytest.mark.parametrize('kind',['docx','pptx','native','scan'])
def test_real_format_face_and_text_transformation(tmp_path,detector,kind):
    directory=create(tmp_path/'sources')
    path=directory/('synthetic-face.docx' if kind=='docx' else 'synthetic-face.pptx' if kind=='pptx' else f'synthetic-face-{kind}.pdf')
    extraction=({'docx':extract_docx,'pptx':extract_pptx,'native':extract_text_pdf,'scan':scan_extraction}[kind])(path)
    original=source_hash(path);extraction.visual=VisualInspectionEngine(detector).inspect(extraction)
    assert any(f.final_decision=='CONFIRM' for f in extraction.visual.faces)
    detection=employee_detection(extraction);redaction=RedactionEngine().redact(extraction,detection)
    engine=DocumentArtifactEngine(tmp_path/'private-output')
    artifact=engine.verify(extraction,redaction,engine.redact(extraction,detection,redaction))
    assert artifact.reopened and artifact.page_count_preserved
    assert artifact.supported_content_verified
    assert artifact.protected_faces>=1 and artifact.face_transformations_verified, artifact.sanitized_summary()
    assert artifact.face_verification_failures==artifact.face_mapping_failures==0
    assert source_hash(path)==original
    assert not artifact.safe_for_llm and not artifact.coverage_verified
    if kind in {'docx','pptx'}:
        output=({'docx':extract_docx,'pptx':extract_pptx}[kind])(artifact.path)
        assert 'EMP-00001' not in output.full_text and '[EMPLOYEE_ID_001]' in output.full_text
        with ZipFile(path) as old,ZipFile(artifact.path) as new:
            for name in old.namelist():
                if name.endswith('.rels'):assert old.read(name)==new.read(name)
                if name.startswith(('word/media','ppt/media')) and name.endswith('.png'):
                    assert old.read(name)!=new.read(name)
        if kind=='pptx':
            picture=next(u for u in extraction.visual.units if u.source_ref.startswith('ppt/media/'))
            assert len(picture.placements)==2
            assert extraction.visual.faces[0].locations==[1,2]
    else:
        with fitz.open(artifact.path) as pdf:
            assert len(pdf)==1 and 'EMP-00001' not in pdf[0].get_text()
            assert '[EMPLOYEE_ID_001]' in pdf[0].get_text()


def test_audit_face_feedback_regeneration_no_detection_and_persistence(tmp_path,detector):
    directory=create(tmp_path/'sources');path=directory/'synthetic-face.pptx';extraction=extract_pptx(path)
    visual=VisualInspectionEngine(detector);inspection=visual.inspect(extraction)
    calls=[]
    pipeline=DocumentPipeline(extraction=SimpleNamespace(extract=lambda p:extraction),
        detection=SimpleNamespace(detect=lambda e:employee_detection(e)),
        visual_detection=SimpleNamespace(inspect=lambda e:calls.append('face') or inspection),
        audit=AuditEngine(tmp_path/'private-audit'),artifact_output_dir=tmp_path/'private-artifact')
    result=pipeline.process(path);assert result.failure is None
    baseline=deepcopy(result.audit_result);record=result.audit_result.visual_records[0]
    assert record.automated_decision=='CONFIRM' and not record.corrected
    text_count=result.detection_result.raw_candidate_count
    rejected=pipeline.apply_feedback(result,ReviewerFeedback('FALSE_POSITIVE','synthetic-reviewer',record.detection_id))
    assert rejected.failure is None and rejected.audit_result.revision==1
    assert rejected.audit_result.visual_records[0].effective_decision=='REJECT'
    assert rejected.artifact_result.protected_faces==0
    again=pipeline.apply_feedback(rejected,ReviewerFeedback('CONFIRM_PII','synthetic-reviewer',record.detection_id,expected_decision='REJECT'))
    assert again.failure is None and again.artifact_result.protected_faces==1
    assert calls==['face'] and result.audit_result==baseline
    assert again.detection_result.raw_candidate_count==text_count
    with ZipFile(result.artifact_result.path) as a,ZipFile(again.artifact_result.path) as b:
        part=next(u.source_ref for u in inspection.units if u.source_ref.startswith('ppt/media/'));assert a.read(part)==b.read(part) # no repeated degradation
    saved=pipeline.save_audit(again);assert saved.failure is None
    loaded=pipeline.load_audit(again.document_id);assert loaded.failure is None and loaded.audit_result==again.audit_result
    assert calls==['face'] and loaded.artifact_result.protected_faces==1
    modified=deepcopy(again.audit_result);modified.visual_records[0].effective_detection.confidence=.1
    with pytest.raises(AuditValidationError):pipeline.audit.get_review_queue(modified)


def test_low_confidence_and_unsupported_media_stay_review(tmp_path):
    path=create(tmp_path/'source')/'synthetic-face.pptx';extraction=extract_pptx(path)
    fake=SimpleNamespace(detect=lambda data:[([.2,.2,.4,.4],.45)])
    extraction.visual=VisualInspectionEngine(fake).inspect(extraction)
    assert extraction.visual.faces[0].final_decision=='REVIEW'
    detection=employee_detection(extraction);audit=AuditEngine().create_audit(extraction,detection,RedactionEngine().redact(extraction,detection))
    assert any(q.category=='visual_review' for q in audit.review_queue)
    assert audit.counts['raw_detection_count']==len(detection.detections) and audit.counts['review']==0


def test_missing_model_failure_stops_pipeline_sanitized(tmp_path):
    path=create(tmp_path/'source')/'synthetic-face.pptx'
    def fail(extraction):raise FaceDetectionError('PRIVATE vendor image details')
    result=DocumentPipeline(visual_detection=SimpleNamespace(inspect=fail)).process(path)
    assert result.failure.stage=='face_detection' and result.artifact_result is None
    assert 'PRIVATE' not in json.dumps(result.sanitized_summary())


def test_tile_passes_are_bounded_and_inference_failures_sanitized(tmp_path):
    detector=FaceDetector();calls=[]
    detector.model=SimpleNamespace(setInputSize=lambda dims:calls.append(dims),detect=lambda frame:(None,None))
    detector.detect(encode(Image.new('RGB',(1800,1200),'white')))
    assert len(calls)==13 and all(max(size)<=1280 for size in calls)
    def fail(frame):raise RuntimeError('PRIVATE image data')
    detector.model.detect=fail
    with pytest.raises(FaceDetectionError) as error:detector.detect(FACE.read_bytes())
    assert 'PRIVATE' not in str(error.value)


def test_cv_unavailable(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules,'cv2',None)
    with pytest.raises(FaceDetectionError):FaceDetector()


def test_serialized_media_tampering_fails_verification(tmp_path,detector):
    path=create(tmp_path/'source')/'synthetic-face.pptx';extraction=extract_pptx(path)
    extraction.visual=VisualInspectionEngine(detector).inspect(extraction)
    detection=employee_detection(extraction);redaction=RedactionEngine().redact(extraction,detection)
    engine=DocumentArtifactEngine(tmp_path/'private-output');result=engine.redact(extraction,detection,redaction)
    part=next(u.source_ref for u in extraction.visual.units if u.source_ref.startswith('ppt/media/'))
    with ZipFile(result.path) as z:members=[(i,z.read(i.filename)) for i in z.infolist()]
    with ZipFile(path) as z:original=z.read(part)
    with ZipFile(result.path,'w') as z:
        for info,data in members:z.writestr(info,original if info.filename==part else data)
    verified=engine.verify(extraction,redaction,result)
    assert not verified.face_transformations_verified and verified.face_verification_failures>0
    assert verified.protected_faces==0 and not verified.safe_for_llm


def test_corrupt_media_inventory_and_invalid_visual_box(tmp_path):
    path=create(tmp_path/'source')/'synthetic-face.pptx'
    with ZipFile(path) as z:members=[(i,z.read(i.filename)) for i in z.infolist()]
    with ZipFile(path,'w') as z:
        for info,data in members:z.writestr(info,b'bad pixels' if info.filename.startswith('ppt/media/') else data)
    # python-pptx does not decode pictures when enumerating slide source parts.
    extraction=extract_pptx(path);inspection=VisualInspectionEngine().inspect(extraction)
    assert inspection.unsupported['image_decode_failed']==1
    good=create(tmp_path/'good')/'synthetic-face.pptx';extraction=extract_pptx(good)
    inspection=VisualInspectionEngine().inspect(extraction);inspection.faces[0].bounding_box=[float('nan'),0,.5,.5]
    with pytest.raises(ValueError):inspection.validate()


def test_duplicate_assets_share_inference_cache(tmp_path):
    path=create(tmp_path/'source')/'synthetic-face.pptx'
    with ZipFile(path) as z:members=[(i,z.read(i.filename)) for i in z.infolist()];portrait=next(d for i,d in members if i.filename.startswith('ppt/media/'))
    with ZipFile(path,'w') as z:
        for info,data in members:z.writestr(info,data)
        z.writestr('ppt/media/unplaced-copy.png',portrait)
    calls=[];detector=SimpleNamespace(detect=lambda data:calls.append(data) or [([.2,.2,.3,.3],.95)])
    inspection=VisualInspectionEngine(detector).inspect(extract_pptx(path))
    assert inspection.cache_hits==1
    assert len(calls)==2 # portrait once + the distinct package thumbnail once
    assert any(f.final_decision=='REVIEW' for f in inspection.faces)
    assert inspection.unsupported['unmapped_visual_placement']==1


def test_native_pdf_reused_face_verified_at_every_placement(tmp_path,detector):
    path=create(tmp_path/'source')/'synthetic-face-native.pdf'
    with fitz.open(path) as doc:
        original=doc[0].get_images(full=True)[0][0]
        second=doc.new_page(width=512,height=620)
        second.insert_image(fitz.Rect(0,0,512,512),xref=original)
        replacement=tmp_path/'reused.pdf';doc.save(replacement)
    extraction=extract_text_pdf(replacement)
    extraction.visual=VisualInspectionEngine(detector).inspect(extraction)
    assert any(u.locations==[1,2] for u in extraction.visual.units)
    detection=employee_detection(extraction);redaction=RedactionEngine().redact(extraction,detection)
    engine=DocumentArtifactEngine(tmp_path/'output')
    result=engine.verify(extraction,redaction,engine.redact(extraction,detection,redaction))
    assert result.face_transformations_verified and result.protected_faces==1
    # First occurrence remains intact. Remove only the second page's image;
    # direct visual verification must detect the missing protected occurrence.
    with fitz.open(result.path) as doc:
        rect=doc[1].rect;doc.delete_page(1);doc.new_page(width=rect.width,height=rect.height)
        tampered=tmp_path/'tampered.pdf';doc.save(tampered)
    result.path=tampered
    from app.engines.redaction.visual_artifacts import verify_visual
    checked=verify_visual(extraction,result,redaction)
    assert not checked.face_transformations_verified and checked.protected_faces==0
