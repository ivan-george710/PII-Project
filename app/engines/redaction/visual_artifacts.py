"""Independent serialized-media verification, never face rediscovery as proof."""
from collections import defaultdict
from hashlib import sha256
from pathlib import PurePosixPath
from zipfile import ZipFile
from io import BytesIO
from math import floor,ceil,isfinite
from PIL import Image,ImageDraw
import pymupdf as fitz
from app.engines.extraction.office import source_hash
from app.engines.visual_detection.inspection import canonical_unit, read_unit
from app.engines.visual_detection.images import decode, encode, blur, pixel_hash


def prepare_visual(extraction,result):
    inspection=extraction.visual
    if inspection is None:return {}
    inspection.validate()
    if inspection.source_sha256!=source_hash(extraction.source_path):raise ValueError('Visual document source changed')
    result.visual_inspection_completed=True
    result.unsupported_visual_content=dict(inspection.unsupported)
    result.known_review_complete=result.known_review_complete and not inspection.unsupported and not any(f.final_decision=='REVIEW' for f in inspection.faces)
    groups=defaultdict(list)
    for f in inspection.faces:
        if f.final_decision in {'CONFIRM','REVIEW'}:groups[f.unit_id].append(f)
    plans={}
    for unit in inspection.units:
        if not groups[unit.unit_id]:continue
        if not unit.mapped:
            result.face_mapping_failures+=len(groups[unit.unit_id]);continue
        with canonical_unit(extraction.source_path,unit) as image:
            transformed,evidence=blur(image,groups[unit.unit_id])
            try:data=encode(transformed,PurePosixPath(unit.source_ref).suffix if unit.kind=='office_media' else '.png')
            finally:transformed.close()
        with decode(data,'raw') as expected:
            check=dict(unit_id=unit.unit_id,kind=unit.kind,source_ref=unit.source_ref,
                expected_sha256=sha256(data).hexdigest(),pixel_sha256=pixel_hash(expected),
                source_pixel_sha256=unit.pixel_sha256,width=unit.width,height=unit.height,
                locations=unit.locations,face_ids=[f.detection_id for f in groups[unit.unit_id]],regions=evidence)
        result.visual_checks.append(check)
        plans[unit.unit_id]=(unit,data,check)
    return plans


def native_images(page,doc,unit,data,check):
    """Replace an embedded payload intrinsically; never guess page transforms."""
    matches=[];existing=[]
    for row in page.get_images(full=True):
        if row[1]:continue
        try:
            with decode(doc.extract_image(row[0])['image'],'raw') as image:
                if image.size!=(unit.width,unit.height):continue
                digest=pixel_hash(image)
            if digest==unit.pixel_sha256:matches.append(row[0])
            elif digest==check['pixel_sha256']:existing.append(row[0])
        except Exception:continue
    for xref in set(matches):page.replace_image(xref,stream=data)
    return bool(matches or existing)


def _output_image(extraction,result,unit,check):
    if unit.kind=='standalone_image':return decode(Path(result.path).read_bytes(),'raw')
    if unit.kind=='office_media':
        with ZipFile(result.path) as z:data=z.read(unit.source_ref)
        if sha256(data).hexdigest()!=check['expected_sha256']:raise ValueError('Encoded media differs')
        with Image.open(BytesIO(data)) as original:
            if original.getexif() or any(k in original.info for k in ('exif','icc_profile','XML:com.adobe.xmp')):raise ValueError('Image metadata retained')
        return decode(data,'raw')
    with fitz.open(result.path) as doc:
        if unit.kind=='pdf_image':
            # Verify every occurrence independently, including shared images on
            # later pages. An intact first occurrence is not sufficient evidence.
            for placement in unit.placements:
                page=doc[placement['location']-1]
                matched=False
                for item in page.get_image_info(xrefs=True):
                    if not item.get('xref'):continue
                    if any(abs(a-b)>1e-4 for a,b in zip(item['bbox'],placement['bbox'])):continue
                    if any(abs(a-b)>1e-4 for a,b in zip(item['transform'],placement['transform'])):continue
                    with decode(doc.extract_image(item['xref'])['image'],'raw') as actual:
                        if actual.size==(unit.width,unit.height) and pixel_hash(actual)==check['pixel_sha256']:
                            matched=True;break
                if not matched:raise ValueError('Expected visual occurrence is not active')
        page=doc[unit.locations[0]-1]
        for row in page.get_images(full=True):
            try:
                data=doc.extract_image(row[0])['image']
                with Image.open(BytesIO(data)) as original:
                    if original.getexif() or any(k in original.info for k in ('exif','icc_profile','XML:com.adobe.xmp')):continue
                image=decode(data,'raw')
                if image.size==(unit.width,unit.height) and pixel_hash(image)==check['pixel_sha256']:return image
                image.close()
            except Exception:continue
    raise ValueError('Expected visual payload not active')


def _compose_raster(extraction,redaction,unit,data,mapping_issues):
    """Independently compose OCR block removal over the original-derived blur."""
    image=decode(data,'raw');draw=ImageDraw.Draw(image)
    page=next(p for p in extraction.pages if p.page_number==unit.locations[0]);blocks=page.blocks or []
    cursor=0;spans=[]
    for b in blocks:spans.append((cursor,cursor+len(b.text)));cursor+=len(b.text)+1
    for record in redaction.redactions if redaction else []:
        if record.page_number!=page.page_number:continue
        if any(i.page_number==record.page_number and i.original_start==record.original_start and i.original_end==record.original_end for i in mapping_issues):continue
        for b,(start,end) in zip(blocks,spans):
            if start>=record.original_end or record.original_start>=end:continue
            points=b.bounding_box
            if len(points)!=4 or any(len(p)!=2 or any(not isfinite(v) for v in p) for p in points):raise ValueError('Invalid OCR composition')
            box=(floor(min(p[0] for p in points)),floor(min(p[1] for p in points)),ceil(max(p[0] for p in points)),ceil(max(p[1] for p in points)))
            draw.rectangle(box,fill='white')
    return image


def verify_visual(extraction,result,redaction=None):
    inspection=extraction.visual
    if inspection is None:return result
    result.face_verification_failures=0;result.protected_face_ids=[];result.face_transformations_verified=False
    expected=type(result)()
    try:
        # Recompute from original/current effective decisions, independently read
        # the generated file, and reject missing/extra/tampered generation evidence.
        plans=prepare_visual(extraction,expected)
        if extraction.file_type in {'docx','pptx'}:
            from .media_artifacts import media_plans, update_face_checks
            media = media_plans(extraction, redaction, {u.source_ref:data for u,data,_ in plans.values()})
            update_face_checks(plans, media)
        if extraction.file_type=='image':
            from .image_artifacts import composed_image
            with composed_image(extraction,redaction,plans) as image:
                payload=encode(image)
                for unit,_,check in plans.values():
                    check['pixel_sha256']=pixel_hash(image)
                    check['expected_sha256']=sha256(payload).hexdigest()
        for unit,data,check in plans.values():
            if unit.kind=='pdf_raster':
                with _compose_raster(extraction,redaction,unit,data,result.mapping_issues) as image:
                    check['composed_pixel_sha256']=pixel_hash(image);check['pixel_sha256']=pixel_hash(image)
        if result.visual_checks!=expected.visual_checks or result.face_mapping_failures!=expected.face_mapping_failures:
            raise ValueError('Face generation evidence differs')
        original_payloads=[]
        for check in expected.visual_checks:
            unit=next(u for u in inspection.units if u.unit_id==check['unit_id'])
            try:
                with _output_image(extraction,result,unit,check) as image:
                    if image.size!=(unit.width,unit.height) or pixel_hash(image)!=check['pixel_sha256']:
                        raise ValueError('Pixels differ from requested transform')
                    if pixel_hash(image)==unit.pixel_sha256:raise ValueError('Original face pixels retained')
                    if image.getexif() or any(k in image.info for k in ('exif','icc_profile','XML:com.adobe.xmp')):
                        raise ValueError('Alternate image metadata retained')
                original_payloads.append(read_unit(extraction.source_path,unit))
                result.protected_face_ids.extend(check['face_ids'])
            except Exception:result.face_verification_failures+=len(check['face_ids'])
        if extraction.file_type in {'docx','pptx'}:
            with ZipFile(result.path) as z:
                # Includes alternate thumbnails/unreferenced media members, not
                # just the visible relationship being displayed in the UI.
                for info in z.infolist():
                    if any(payload in z.read(info) for payload in original_payloads):
                        result.face_verification_failures+=1
        elif extraction.file_type=='pdf':
            with fitz.open(result.path) as doc:
                for xref in range(1,doc.xref_length()):
                    if not doc.xref_is_image(xref):continue
                    try:
                        with decode(doc.extract_image(xref)['image'],'raw') as image:
                            if any(u.kind=='pdf_image' and image.size==(u.width,u.height) and pixel_hash(image)==u.pixel_sha256
                                   for u in inspection.units if any(f.unit_id==u.unit_id and f.final_decision in {'CONFIRM','REVIEW'} for f in inspection.faces)):
                                result.face_verification_failures+=1
                    except Exception:continue
        if not result.reopened:result.face_verification_failures+=1
        if result.face_verification_failures:result.protected_face_ids=[]
    except Exception:
        result.face_verification_failures+=1;result.protected_face_ids=[]
    result.protected_faces=len(result.protected_face_ids)
    result.face_transformations_verified=(result.face_mapping_failures==0 and result.face_verification_failures==0
                                          and not result.unsupported_visual_content)
    return result


def visual_crop(extraction,result,face,after=False):
    from app.engines.visual_detection.images import pixel_box
    unit=next(u for u in extraction.visual.units if u.unit_id==face.unit_id)
    if after:
        if result is None or face.detection_id not in result.protected_face_ids:raise ValueError('No verified face output')
        check=next(c for c in result.visual_checks if face.detection_id in c['face_ids'])
        image=_output_image(extraction,result,unit,check)
    else:image=canonical_unit(extraction.source_path,unit)
    with image:
        crop=image.crop(pixel_box(face.bounding_box,*image.size));crop.thumbnail((512,512))
        try:return encode(crop)
        finally:crop.close()
