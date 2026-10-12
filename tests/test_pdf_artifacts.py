"""Destructive PDF artifacts, trusted OCR mappings and fresh-source review feedback."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import json

import pymupdf as fitz
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas
import pytest

from app.engines.extraction.pdf import extract_text_pdf
from app.engines.extraction.models import ExtractionResult, ExtractedPage, OCRTextBlock, PDFSourceMap
from app.engines.extraction.office import source_hash
from app.engines.pii_detection.models import DetectedPII, PIIDetectionResult
from app.engines.redaction import RedactionEngine
from app.engines.redaction.pdf_artifacts import PDFArtifactEngine, ArtifactValidationError
from app.engines.audit import AuditEngine, ReviewerFeedback
from app.pipeline import DocumentPipeline


def finding(extraction,value,entity="EMPLOYEE_ID",decision="CONFIRM",page=1):
    text=extraction.pages[page-1].text
    start=text.index(value)
    return DetectedPII(entity,value,start,start+len(value),.9,"pattern","Synthetic",page,
        validation_decision="AMBIGUOUS" if decision=="REVIEW" else decision,final_decision=decision)


def detection_for(extraction,*items):
    return PIIDetectionResult(extraction.source_path,extraction.filename,
        [d for d in items if d.final_decision=="CONFIRM"],[],
        [d for d in items if d.final_decision=="REVIEW"],len(items),[p.page_number for p in extraction.pages])


def native(tmp_path):
    path=tmp_path/"original.pdf"
    pdf=canvas.Canvas(str(path))
    pdf.drawString(50,700,"Employee EMP-00001")
    pdf.drawString(50,650,"Keep business content")
    pdf.drawString(50,600,"Missing code EMP-00002")
    pdf.showPage()
    pdf.drawString(50,700,"Unrelated second page")
    pdf.save()
    return path,extract_text_pdf(path)


def scanned(tmp_path):
    image=Image.new("RGB",(612,792),"white")
    draw=ImageDraw.Draw(image)
    draw.text((100,100),"EMP-00001",fill="black",font_size=24)
    draw.text((100,250),"Keep image content",fill="black",font_size=24)
    png=tmp_path/"source.png"
    image.save(png)
    path=tmp_path/"scan.pdf"
    pdf=canvas.Canvas(str(path),pagesize=(612,792))
    pdf.drawImage(str(png),0,0,width=612,height=792)
    pdf.save()
    block=OCRTextBlock("EMP-00001",.99,[[90,95],[270,95],[270,145],[90,145]])
    extraction=ExtractionResult(path,path.name,"pdf",[ExtractedPage(1,block.text,"ocr",[block])],
        pdf_source=PDFSourceMap(source_hash(path),{"1":72}))
    return path,extraction


@pytest.mark.parametrize("kind",["native","scanned"])
def test_destructive_output_reopens_preserves_source_and_regions(tmp_path,kind):
    path,extraction=(native if kind=="native" else scanned)(tmp_path)
    before=path.read_bytes()
    detection=detection_for(extraction,finding(extraction,"EMP-00001"))
    redaction=RedactionEngine().redact(extraction,detection)
    engine=PDFArtifactEngine(tmp_path/"private-artifacts")
    artifact=engine.verify(extraction,redaction,engine.redact(extraction,detection,redaction))
    assert artifact.reopened and artifact.supported_content_verified
    assert artifact.page_count_preserved and artifact.mapping_issue_count==artifact.verification_failure_count==0
    assert artifact.format=="pdf" and artifact.output_path.suffix==".pdf"
    assert artifact.applied_redactions==1 and path.read_bytes()==before
    with fitz.open(artifact.path) as output:
        assert len(output)==len(extraction.pages)
        text="\n".join(p.get_text() for p in output)
        assert "EMP-00001" not in text and "[EMPLOYEE_ID_001]" in text
        if kind=="native":
            assert "Keep business content" in text and "Unrelated second page" in text
            assert "EMP-00002" in text
            assert not any(p.first_annot for p in output)  # Applied destructive redactions, not annotations/overlay.
        else:
            image=fitz.Pixmap(output,output[0].get_images(full=True)[0][0])
            pixels=Image.frombytes("RGB",(image.width,image.height),image.samples)
            assert pixels.crop((90,95,270,145)).getextrema()==((255,255),(255,255),(255,255))
            assert pixels.crop((90,240,400,290)).getextrema()[0][0]<255  # Unrelated image text retained.
    summary=json.dumps(artifact.sanitized_summary())
    assert str(path) not in summary and "EMP-00001" not in summary
    assert not artifact.safe_for_llm and not artifact.coverage_verified


def test_hybrid_native_and_ocr_pages(tmp_path):
    native_path,native_result=native(tmp_path)
    scan_dir=tmp_path/"scan"
    scan_dir.mkdir()
    scan_path,scan_result=scanned(scan_dir)
    path=tmp_path/"hybrid.pdf"
    with fitz.open(native_path) as a, fitz.open(scan_path) as b, fitz.open() as out:
        out.insert_pdf(a,from_page=0,to_page=0)
        out.insert_pdf(b)
        out.save(path)
    extraction=ExtractionResult(path,path.name,"pdf",[
        native_result.pages[0],ExtractedPage(2,scan_result.pages[0].text,"ocr",scan_result.pages[0].blocks)],
        pdf_source=PDFSourceMap(source_hash(path),{"2":72}))
    d=detection_for(extraction,finding(extraction,"EMP-00001"),finding(extraction,"EMP-00001",page=2))
    r=RedactionEngine().redact(extraction,d)
    engine=PDFArtifactEngine(tmp_path/"private-artifacts")
    artifact=engine.verify(extraction,r,engine.redact(extraction,d,r))
    assert artifact.supported_content_verified and artifact.applied_redactions==2
    assert artifact.page_count_preserved


@pytest.mark.parametrize("fault",["bbox","block_text","native_text"])
def test_unreliable_mapping_fails_closed(tmp_path,fault):
    path,e=(native if fault=="native_text" else scanned)(tmp_path)
    if fault=="bbox": e.pages[0].blocks[0].bounding_box[0][0]=-99
    elif fault=="block_text": e.pages[0].blocks[0].text="Different OCR text"
    else: e.pages[0].text="EMP-00001 unverified extraction"
    d=detection_for(e,finding(e,"EMP-00001"))
    r=RedactionEngine().redact(e,d)
    engine=PDFArtifactEngine(tmp_path/"private-artifacts")
    a=engine.verify(e,r,engine.redact(e,d,r))
    assert a.mapping_failures==1 and a.verification_failures>0
    assert not a.supported_content_verified and not a.safe_for_llm


def test_pdf_feedback_actions_regenerate_without_detection_or_source_extraction(tmp_path):
    path,e=native(tmp_path)
    d=detection_for(e,finding(e,"EMP-00001",decision="REVIEW"))
    pipeline=DocumentPipeline(extraction=SimpleNamespace(extract=Mock(return_value=e)),
        detection=SimpleNamespace(detect=Mock(return_value=d)),audit=AuditEngine(tmp_path/"private-audit"),
        artifact_output_dir=tmp_path/"private-artifacts")
    result=pipeline.process(path)
    assert result.failure is None
    original=deepcopy(result)
    target=result.audit_result.records[0].detection_id
    confirmed=pipeline.apply_feedback(result,ReviewerFeedback("CONFIRM_PII","reviewer",target))
    assert confirmed.failure is None and confirmed.artifact_result.supported_content_verified
    false=pipeline.apply_feedback(confirmed,ReviewerFeedback("FALSE_POSITIVE","reviewer",target,expected_decision="CONFIRM"))
    assert false.failure is None
    with fitz.open(false.artifact_result.path) as doc: assert "EMP-00001" in doc[0].get_text()
    page=e.pages[0]
    start=page.text.index("EMP-00002")
    missed=pipeline.apply_feedback(false,ReviewerFeedback("MISSED_PII","reviewer",page_number=1,
        original_start=start,original_end=start+9,entity_type="EMPLOYEE_ID"))
    assert missed.failure is None and missed.artifact_result.supported_content_verified
    with fitz.open(missed.artifact_result.path) as doc:
        assert "EMP-00002" not in doc[0].get_text() and "EMP-00001" in doc[0].get_text()
    assert pipeline.extraction.extract.call_count==pipeline.detection.detect.call_count==1
    assert result==original and len(missed.audit_result.feedback)==3
    assert len({r.artifact_result.path for r in [result,confirmed,false,missed]})==4
    assert not missed.safe_for_llm


def test_source_integrity_and_missing_fingerprint_block_generation(tmp_path):
    path,e=native(tmp_path)
    d=detection_for(e,finding(e,"EMP-00001"))
    r=RedactionEngine().redact(e,d)
    engine=PDFArtifactEngine(tmp_path/"private-artifacts")
    old=e.pdf_source
    e.pdf_source=None
    with pytest.raises(ArtifactValidationError): engine.redact(e,d,r)
    e.pdf_source=old
    path.write_bytes(path.read_bytes()+b"changed")
    with pytest.raises(ArtifactValidationError): engine.redact(e,d,r)


def test_overlay_tampering_is_detected(tmp_path):
    path,e=native(tmp_path)
    d=detection_for(e,finding(e,"EMP-00001"))
    r=RedactionEngine().redact(e,d)
    engine=PDFArtifactEngine(tmp_path/"private-artifacts")
    a=engine.redact(e,d,r)
    with fitz.open(a.path) as out:
        out[0].insert_text((50,142),"EMP-00001",fontsize=12)
        out.saveIncr()
    checked=engine.verify(e,r,a)
    assert checked.verification_failures>0 and not checked.supported_content_verified


@pytest.mark.parametrize("mode",["trailing_separator","multiple_blocks"])
def test_ocr_proven_block_boundaries(tmp_path,mode):
    path,e=scanned(tmp_path)
    first=e.pages[0].blocks[0]
    if mode=="trailing_separator":
        second=OCRTextBlock("Keep image content",.9,[[90,240],[400,240],[400,290],[90,290]])
        text=first.text+"\n"+second.text
        value=first.text+"\n"
    else:
        first.text="EMP-"
        second=OCRTextBlock("00001 Keep",.9,[[90,240],[400,240],[400,290],[90,290]])
        text=first.text+"\n"+second.text
        value="EMP-\n00001"
    e.pages[0].blocks=[first,second]
    e.pages[0].text=text
    d=detection_for(e,finding(e,value))
    r=RedactionEngine().redact(e,d)
    engine=PDFArtifactEngine(tmp_path/"private-artifacts")
    artifact=engine.verify(e,r,engine.redact(e,d,r))
    assert artifact.mapping_failures==artifact.verification_failures==0
    assert artifact.supported_content_verified and artifact.applied_redactions==1
    with fitz.open(artifact.path) as doc:
        assert "[EMPLOYEE_ID_001]" in doc[0].get_text()
        if mode=="multiple_blocks": assert "Keep" in doc[0].get_text()
