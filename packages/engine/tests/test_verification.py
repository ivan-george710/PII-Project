"""Actual serialized outputs and deliberate regressions, not writer success flags."""
from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile
import traceback

import pymupdf
import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject, DecodedStreamObject, DictionaryObject

from pii_guard.models import SourceLocation, Finding
from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.rules.policy import RedactionTarget
from pii_guard.redaction import redact_image, redact_pdf, redact_text
from pii_guard.verification import (
    prepare_verification, verify_artifact, prepare_text_verification, verify_text, VerificationContext,
)
from test_redaction import _pdf_case, _office_case, _office_renderer, _raster, _zip_change


MIMES={'png':'image/png','jpeg':'image/jpeg','pdf':'application/pdf',
    'docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'pptx':'application/vnd.openxmlformats-officedocument.presentationml.presentation'}
MARKER='VERIFICATION_PRIVATE_710'


def safe_failure(call,caplog):
    with pytest.raises(ProcessingError) as caught:call()
    assert caught.value.code==ProcessingErrorCode.REDACTION_FAILED
    assert 'SECRET' not in ''.join(traceback.format_exception(caught.value))
    assert MARKER not in ''.join(traceback.format_exception(caught.value))
    assert MARKER not in caplog.text


def case(tmp_path,kind,*,mixed=True,rotation=0,crop=False):
    aid=uuid4();blocks=[];sources=[]
    if kind in {'png','jpeg'}:
        original=_raster()
        if kind=='jpeg':
            b=BytesIO()
            with Image.open(BytesIO(original)) as im:im.save(b,format='JPEG')
            original=b.getvalue()
        source=SourceLocation(artifact_id=aid,kind='ocr',page_number=None,slide_number=None,source_ref='image:ocr:0',start=0,end=6,bbox=(.1,.2,.3,.3))
        sources=[source];targets=[RedactionTarget(finding_id=uuid4(),location=source)]
        output=redact_image(original,targets,artifact_id=aid,sources=sources).data
    elif kind=='pdf':
        path,aid,blocks,targets=_pdf_case(tmp_path,image=mixed,rotation=rotation,crop=crop)
        original=path.read_bytes();output=redact_pdf(original,targets,artifact_id=aid,blocks=blocks)
    else:
        path,aid,blocks,targets=_office_case(tmp_path,kind,shared=True)
        original=path.read_bytes();output=_office_renderer(kind)(original,targets,artifact_id=aid,blocks=blocks)
    # This evidence comes only from the original, never from the writer's output.
    evidence=prepare_verification(original,artifact_id=aid,mime_type=MIMES[kind],targets=targets,blocks=blocks,sources=sources)
    path=tmp_path/f'output.{kind}';path.write_bytes(output)
    return path,aid,evidence,original,blocks,targets,sources


@pytest.mark.parametrize('kind',list(MIMES))
def test_actual_sanitized_artifacts_verify_and_remain_unchanged(tmp_path,kind):
    path,aid,evidence,_,_,_,_=case(tmp_path,kind)
    before=path.read_bytes()
    assert verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES[kind]) is None
    assert path.read_bytes()==before
    assert evidence.model_dump()=={} and evidence.model_dump_json()=='{}'
    assert 'SECRET' not in repr(evidence) and 'sha256' not in repr(evidence)
    assert not list(tmp_path.glob('.pii-verification-*'))


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_pdf_page_geometry_and_underlying_rasters_verify(tmp_path,rotation,crop):
    path,aid,evidence,*_=case(tmp_path,'pdf',rotation=rotation,crop=crop)
    verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES['pdf'])


@pytest.mark.parametrize('kind',['png','jpeg'])
@pytest.mark.parametrize('tamper',['original','hole','transparent','metadata','dimensions'])
def test_image_regressions_are_detected(tmp_path,kind,tamper,caplog):
    path,aid,evidence,original,_,_,_=case(tmp_path,kind)
    if tamper=='original':path.write_bytes(original)
    else:
        with Image.open(path) as im:
            changed=im.convert('RGBA' if tamper=='transparent' else 'RGB')
        if tamper=='hole':changed.putpixel((40,30),(250,250,250))
        elif tamper=='transparent':changed.putpixel((40,30),(0,0,0,0))
        elif tamper=='dimensions':changed=changed.resize((100,50))
        b=BytesIO();options={}
        if tamper=='metadata':
            exif=Image.Exif();exif[270]=MARKER;options['exif']=exif
        changed.save(b,format='PNG' if kind=='png' or tamper=='transparent' else 'JPEG',**options)
        path.write_bytes(b.getvalue())
    safe_failure(lambda:verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES[kind]),caplog)
    assert path.exists()  # Deletion belongs to the staging owner.


@pytest.mark.parametrize('orientation',range(1,9))
def test_standalone_exif_oriented_regions_are_verified(tmp_path,orientation):
    im=Image.new('RGB',(60,40),'white');exif=Image.Exif();exif[274]=orientation
    b=BytesIO();im.save(b,format='PNG',exif=exif);original=b.getvalue();aid=uuid4()
    source=SourceLocation(artifact_id=aid,kind='ocr',page_number=None,slide_number=None,source_ref='image:ocr:0',start=0,end=6,bbox=(.1,.2,.3,.3))
    targets=[RedactionTarget(finding_id=uuid4(),location=source)]
    context=prepare_verification(original,artifact_id=aid,mime_type=MIMES['png'],targets=targets,sources=[source])
    path=tmp_path/'oriented.png';path.write_bytes(redact_image(original,targets,artifact_id=aid,sources=[source]).data)
    verify_artifact(path,context,artifact_id=aid,mime_type=MIMES['png'])


@pytest.mark.parametrize('mode',['native_survives','image_survives','overlay','attachment','xmp','action','annotation','geometry','orphan'])
def test_pdf_tampering_cannot_pass_verification(tmp_path,mode,caplog):
    path,aid,evidence,original,blocks,targets,_=case(tmp_path,'pdf')
    if mode=='native_survives':
        path.write_bytes(redact_pdf(original,[t for t in targets if t.location.kind=='ocr'],artifact_id=aid,blocks=blocks))
    elif mode in {'image_survives','overlay'}:
        path.write_bytes(redact_pdf(original,[t for t in targets if t.location.kind=='native_text'],artifact_id=aid,blocks=blocks))
        if mode=='overlay':
            with pymupdf.open(path) as doc:
                loc=next(t.location for t in targets if t.location.kind=='ocr');x,y,w,h=loc.bbox;p=doc[0]
                p.draw_rect(pymupdf.Rect(x*p.rect.width,y*p.rect.height,(x+w)*p.rect.width,(y+h)*p.rect.height),fill=(0,0,0))
                data=doc.tobytes()
            path.write_bytes(data)
    else:
        writer=PdfWriter(clone_from=PdfReader(path))
        if mode=='attachment':writer.add_attachment('private.txt',MARKER.encode())
        elif mode=='xmp':
            s=DecodedStreamObject();s.set_data(MARKER.encode());writer._root_object[NameObject('/Metadata')]=writer._add_object(s)
        elif mode=='action':writer._root_object[NameObject('/OpenAction')]=TextStringObject(MARKER)
        elif mode=='annotation':writer.pages[0][NameObject('/Annots')]=DictionaryObject({NameObject('/Private'):TextStringObject(MARKER)})
        elif mode=='geometry':writer.pages[0].rotate(90)
        else:
            s=DecodedStreamObject();s.set_data(MARKER.encode());writer._add_object(s)
        b=BytesIO();writer.write(b);path.write_bytes(b.getvalue())
    safe_failure(lambda:verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES['pdf']),caplog)


@pytest.mark.parametrize('kind',['docx','pptx'])
@pytest.mark.parametrize('mode',['text','metadata','hidden_part','external','media','geometry','description'])
def test_office_tampered_serialized_members_fail(tmp_path,kind,mode,caplog):
    path,aid,evidence,original,_,_,_=case(tmp_path,kind)
    def tamper(parts):
        part='word/document.xml' if kind=='docx' else 'ppt/slides/slide1.xml'
        if mode=='text':parts[part]=parts[part].replace(b'[REDACTED]',b'SECRET',1)
        elif mode=='metadata':parts['docProps/core.xml']=b'<private>'+MARKER.encode()+b'</private>'
        elif mode=='hidden_part':parts['customXml/private.xml']=b'<private>'+MARKER.encode()+b'</private>'
        elif mode=='external':
            name='word/_rels/document.xml.rels' if kind=='docx' else 'ppt/slides/_rels/slide1.xml.rels'
            parts[name]=parts[name].replace(b'Target="',b'TargetMode="External" Target="',1)
        elif mode=='media':
            with ZipFile(BytesIO(original)) as z:
                name=next(n for n in parts if '/media/' in n);parts[name]=z.read(name)
        elif mode=='geometry':
            if kind=='pptx':parts['ppt/presentation.xml']=parts['ppt/presentation.xml'].replace(b'cx="9144000"',b'cx="10000000"')
            else:parts[part]=parts[part].replace(b'r:embed="rId',b'r:embed="rId999',1)
        else:parts[part]=parts[part].replace(b'name=""',b'name="'+MARKER.encode()+b'"',1)
    path.write_bytes(_zip_change(path.read_bytes(),tamper))
    safe_failure(lambda:verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES[kind]),caplog)


def test_powerpoint_note_leak_detected_separately_from_shape_text(tmp_path,caplog):
    path,aid,evidence,*_=case(tmp_path,'pptx')
    def tamper(parts):
        name=next(n for n in parts if n.startswith('ppt/notesSlides/notesSlide') and n.endswith('.xml'))
        parts[name]=parts[name].replace(b'[REDACTED]',b'SECRET')
    path.write_bytes(_zip_change(path.read_bytes(),tamper))
    safe_failure(lambda:verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES['pptx']),caplog)


@pytest.mark.parametrize('kind',list(MIMES))
@pytest.mark.parametrize('mode',['missing','empty','truncated','wrong_bytes','directory','wrong_mime','wrong_id','unprepared'])
def test_common_failures_are_safe_and_do_not_delete_outputs(tmp_path,kind,mode,caplog):
    path,aid,evidence,*_=case(tmp_path,kind)
    mime=MIMES[kind]
    if mode=='missing':path.unlink()
    elif mode=='empty':path.write_bytes(b'')
    elif mode=='truncated':path.write_bytes(path.read_bytes()[:40])
    elif mode=='wrong_bytes':path.write_bytes(MARKER.encode())
    elif mode=='directory':path.unlink();path.mkdir()
    elif mode=='wrong_mime':mime='application/octet-stream'
    elif mode=='wrong_id':aid=uuid4()
    else:evidence=VerificationContext()
    safe_failure(lambda:verify_artifact(path,evidence,artifact_id=aid,mime_type=mime),caplog)
    assert not list(tmp_path.glob('.pii-verification-*'))


@pytest.mark.parametrize('kind',list(MIMES))
@pytest.mark.parametrize('field',['artifact_id','source_ref','end'])
def test_original_target_mismatch_fails_during_evidence_preparation(tmp_path,kind,field,caplog):
    _,aid,_,original,blocks,targets,sources=case(tmp_path,kind)
    update={'artifact_id':uuid4(),'source_ref':'impossible:source','end':1000001}
    targets[0]=targets[0].model_copy(update={'location':targets[0].location.model_copy(update={field:update[field]})})
    safe_failure(lambda:prepare_verification(original,artifact_id=aid,mime_type=MIMES[kind],targets=targets,blocks=blocks,sources=sources),caplog)


def test_message_verification_independent_unicode_overlaps_and_duplicate_values(caplog):
    original='😀 e\u0301 SECRET\nSECRET public!'
    lo=original.index('SECRET');source=SourceLocation(artifact_id=None,kind='message',page_number=None,slide_number=None,source_ref=None,start=0,end=len(original),bbox=None)
    targets=[RedactionTarget(finding_id=uuid4(),location=source.model_copy(update={'start':lo,'end':lo+6})),
        RedactionTarget(finding_id=uuid4(),location=source.model_copy(update={'start':lo+2,'end':lo+4}))]
    expected=original[:lo]+'[REDACTED]'+original[lo+6:]
    evidence=prepare_text_verification(original,reversed(targets))
    verify_text(expected,evidence)
    assert 'SECRET' in expected  # Legitimate duplicate is deliberately retained.
    safe_failure(lambda:verify_text(original,evidence),caplog)
    assert evidence.model_dump()=={} and original not in repr(evidence)


@pytest.mark.parametrize('kind',['docx','pptx'])
def test_duplicate_native_values_in_other_units_remain_valid(tmp_path,kind):
    path,aid,blocks,targets=_office_case(tmp_path,kind,pictures=False)
    targets=targets[:1]  # Other paragraphs/notes contain the same value, allowed.
    original=path.read_bytes()
    evidence=prepare_verification(original,artifact_id=aid,mime_type=MIMES[kind],targets=targets,blocks=blocks)
    path=tmp_path/f'duplicate.{kind}';path.write_bytes(_office_renderer(kind)(original,targets,artifact_id=aid,blocks=blocks))
    verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES[kind])


def test_text_evidence_source_identity_and_public_finding_are_unchanged(caplog):
    loc=SourceLocation(artifact_id=uuid4(),kind='native_text',page_number=None,slide_number=None,source_ref='unit:1',start=0,end=6,bbox=None)
    event=Finding(id=uuid4(),rule_id='EMPLOYEE_ID',category='employment',confidence=1,
        recognizer='synthetic',location=loc,action='redacted')
    target=RedactionTarget(finding_id=event.id,location=loc);before=event.model_dump_json()
    evidence=prepare_text_verification('SECRET',[target],source=loc)
    verify_text('[REDACTED]',evidence,source=loc)
    safe_failure(lambda:verify_text('[REDACTED]',evidence,source=loc.model_copy(update={'source_ref':'unit:2'})),caplog)
    assert event.model_dump_json()==before and evidence.model_dump_json()=='{}'


def test_optional_fixture_fingerprints_scan_decoded_pdf_objects(tmp_path,caplog):
    path,aid,blocks,targets=_pdf_case(tmp_path,image=False)
    original=path.read_bytes()
    evidence=prepare_verification(original,artifact_id=aid,mime_type=MIMES['pdf'],targets=targets,blocks=blocks,verification_markers=[MARKER])
    path.write_bytes(redact_pdf(original,targets,artifact_id=aid,blocks=blocks))
    verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES['pdf'])
    # A reachable resource name can carry a fixture marker despite being needed
    # structurally; the independent decoded-object scan must catch it.
    writer=PdfWriter(clone_from=PdfReader(path))
    page=writer.pages[0];fonts=page['/Resources']['/Font'];old=next(iter(fonts));font=fonts.pop(old)
    new=NameObject('/'+MARKER);fonts[new]=font
    if '/Name' in font.get_object():font.get_object()[NameObject('/Name')]=new
    content=page['/Contents'].get_object()
    if isinstance(content,list):content=content[0].get_object()
    content.set_data(content.get_data().replace(str(old).encode(),str(new).encode()))
    b=BytesIO();writer.write(b);path.write_bytes(b.getvalue())
    safe_failure(lambda:verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES['pdf']),caplog)


@pytest.mark.parametrize('kind',list(MIMES))
def test_original_file_fingerprint_rejects_swapping_sources(tmp_path,kind,caplog):
    path,aid,evidence,original,*_=case(tmp_path,kind)
    source=tmp_path/f'original.{kind}';source.write_bytes(original)
    verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES[kind],original_path=source)
    assert source.read_bytes()==original
    source.write_bytes(original+b'changed')
    safe_failure(lambda:verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES[kind],original_path=source),caplog)
    assert source.read_bytes()==original+b'changed' and path.exists()


@pytest.mark.parametrize('kind',list(MIMES))
def test_verification_never_invokes_a_redactor(tmp_path,kind,monkeypatch):
    path,aid,evidence,*_=case(tmp_path,kind)
    def forbidden(*args,**kwargs):raise AssertionError('Writer invoked by verifier')
    for name in ['text','image','pdf','docx','pptx']:
        monkeypatch.setattr(f'pii_guard.redaction.{name}.redact_{name}',forbidden)
    verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES[kind])


def test_jpeg_dark_readable_payload_does_not_pass_edge_tolerance(tmp_path,caplog):
    from PIL import ImageDraw
    path,aid,evidence,*_=case(tmp_path,'jpeg')
    with Image.open(path) as im:changed=im.convert('RGB')
    ImageDraw.Draw(changed).text((30,28),'PII',fill=(30,30,30))
    changed.save(path,format='JPEG',quality=95,subsampling=0)
    safe_failure(lambda:verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES['jpeg']),caplog)


@pytest.mark.parametrize('kind',['docx','pptx','pdf'])
def test_no_enabled_targets_still_verifies_structure_and_preserved_content(tmp_path,kind):
    _,aid,_,original,blocks,_,_=case(tmp_path,kind)
    evidence=prepare_verification(original,artifact_id=aid,mime_type=MIMES[kind],blocks=blocks)
    output=redact_pdf(original,artifact_id=aid,blocks=blocks) if kind=='pdf' else _office_renderer(kind)(original,artifact_id=aid,blocks=blocks)
    path=tmp_path/f'no_targets.{kind}';path.write_bytes(output)
    verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES[kind])


def test_evidence_is_private_even_when_nested_and_mutation_does_not_change_run(tmp_path):
    from pydantic import BaseModel
    class Envelope(BaseModel):
        verification:VerificationContext
    path,aid,evidence,_,_,targets,_=case(tmp_path,'png')
    before=evidence.model_dump_json()
    targets[0].location.bbox=(.5,.5,.1,.1)
    verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES['png'])
    assert Envelope(verification=evidence).model_dump()=={'verification':{}}
    assert evidence.model_dump_json()==before


@pytest.mark.parametrize('value',['','plain unicode 😀\ntext'])
def test_message_no_targets_and_empty_text(value):
    evidence=prepare_text_verification(value)
    verify_text(value,evidence)


def test_invalid_message_targets_fail_closed(caplog):
    loc=SourceLocation(artifact_id=None,kind='message',page_number=None,slide_number=None,source_ref=None,start=0,end=999,bbox=None)
    original='SECRET'
    safe_failure(lambda:prepare_text_verification(original,[RedactionTarget(finding_id=uuid4(),location=loc)]),caplog)


def test_pdf_duplicate_sensitive_values_on_another_page_are_allowed(tmp_path):
    from reportlab.pdfgen import canvas
    from pii_guard.extraction import extract_pdf
    b=BytesIO();drawing=canvas.Canvas(b,pagesize=(300,200))
    for _ in range(2):drawing.drawString(30,175,'SECRET public');drawing.showPage()
    drawing.save();original=b.getvalue();aid=uuid4();source=tmp_path/'duplicate-source.pdf';source.write_bytes(original)
    class NoOCR:
        def recognize_image(self,*args,**kwargs):raise AssertionError('Native text needs no OCR')
    blocks=extract_pdf(source,artifact_id=aid,filename=source.name,ocr_provider=NoOCR()).blocks
    loc=blocks[0].location.model_copy(update={'start':0,'end':6})
    targets=[RedactionTarget(finding_id=uuid4(),location=loc)]
    evidence=prepare_verification(original,artifact_id=aid,mime_type=MIMES['pdf'],blocks=blocks,targets=targets)
    output=tmp_path/'duplicate-output.pdf';output.write_bytes(redact_pdf(original,targets,artifact_id=aid,blocks=blocks))
    verify_artifact(output,evidence,artifact_id=aid,mime_type=MIMES['pdf'])
    assert 'SECRET' in PdfReader(output).pages[1].extract_text()


@pytest.mark.parametrize('kind',['png','jpeg'])
def test_enabled_target_order_and_duplicate_regions_do_not_change_verification(tmp_path,kind):
    path,aid,_,original,blocks,targets,sources=case(tmp_path,kind)
    evidence=prepare_verification(original,artifact_id=aid,mime_type=MIMES[kind],blocks=blocks,sources=sources,targets=[*reversed(targets),*targets])
    verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES[kind])


@pytest.mark.parametrize('source_kind',['png','jpeg'])
def test_declared_png_jpeg_conversion_is_verified(tmp_path,source_kind):
    _,aid,_,original,_,targets,sources=case(tmp_path,source_kind)
    output_kind='jpeg' if source_kind=='png' else 'png'
    evidence=prepare_verification(original,artifact_id=aid,mime_type=MIMES[source_kind],output_mime=MIMES[output_kind],targets=targets,sources=sources)
    path=tmp_path/f'converted.{output_kind}'
    path.write_bytes(redact_image(original,targets,artifact_id=aid,sources=sources,output_format='PNG' if output_kind=='png' else 'JPEG').data)
    verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES[output_kind])


@pytest.mark.parametrize('field',['font_type','image_type','profile'])
def test_pdf_structural_objects_cannot_carry_reintroduced_private_payloads(tmp_path,field,caplog):
    path,aid,evidence,*_=case(tmp_path,'pdf')
    writer=PdfWriter(clone_from=PdfReader(path));res=writer.pages[0]['/Resources']
    if field=='font_type':next(iter(res['/Font'].values())).get_object()[NameObject('/Type')]=NameObject('/'+MARKER)
    else:
        image=next(iter(res['/XObject'].values())).get_object()
        if field=='image_type':image[NameObject('/Type')]=NameObject('/'+MARKER)
        else:image['/ColorSpace'][1].get_object().set_data(MARKER.encode())
    b=BytesIO();writer.write(b);path.write_bytes(b.getvalue())
    safe_failure(lambda:verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES['pdf']),caplog)


def test_verification_bounds_fail_closed_without_leaking_payload(caplog):
    from pii_guard.verification.pdf import _bounded_stream
    from pii_guard.verification.artifact import _markers_absent
    from hashlib import sha256
    stream=DecodedStreamObject();stream.set_data(MARKER.encode());stream[NameObject('/Filter')]=NameObject('/Unsupported')
    with pytest.raises(ValueError) as error:_bounded_stream(stream)
    assert MARKER not in str(error.value)
    with pytest.raises(ValueError):_markers_absent([b'x'*2000010],[(4,sha256(b'none').digest())])


def test_jpeg_unverifiable_tiny_region_fails_closed(tmp_path,caplog):
    _,aid,_,original,_,_,_=case(tmp_path,'jpeg')
    source=SourceLocation(artifact_id=aid,kind='ocr',page_number=None,slide_number=None,source_ref='image:ocr:0',start=0,end=6,bbox=(.1,.2,.005,.01))
    targets=[RedactionTarget(finding_id=uuid4(),location=source)]
    evidence=prepare_verification(original,artifact_id=aid,mime_type=MIMES['jpeg'],targets=targets,sources=[source])
    path=tmp_path/'tiny.jpeg';path.write_bytes(redact_image(original,targets,artifact_id=aid,sources=[source]).data)
    safe_failure(lambda:verify_artifact(path,evidence,artifact_id=aid,mime_type=MIMES['jpeg']),caplog)
