"""Image-level inspection with deterministic package/raster references."""
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path, PurePosixPath
from io import BytesIO
import posixpath
from time import perf_counter
from zipfile import ZipFile
from math import isfinite
import pymupdf as fitz
from PIL import Image
from app.engines.extraction.office import parse_xml, source_hash
from .models import VisualUnit, FaceDetection, VisualInspection
from .images import decode, encode, pixel_hash, MAX_BYTES
from .detector import FaceDetector

R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


def read_unit(path, unit):
    if unit.kind=='standalone_image':return Path(path).read_bytes()
    if unit.kind=='office_media':
        with ZipFile(path) as z:
            if z.getinfo(unit.source_ref).file_size>MAX_BYTES:raise ValueError('Oversized media')
            return z.read(unit.source_ref)
    with fitz.open(path) as doc:
        if unit.kind=='pdf_image':return doc.extract_image(int(unit.source_ref.split(':')[1]))['image']
        page_number,dpi=map(int,unit.source_ref.split(':')[1:])
        pix=doc[page_number-1].get_pixmap(dpi=dpi,colorspace=fitz.csRGB,alpha=False,annots=False)
        return pix.tobytes('png')


def canonical_unit(path, unit):
    data=read_unit(path,unit)
    image=decode(data,unit.frame)
    if sha256(data).hexdigest()!=unit.image_sha256 or image.size!=(unit.width,unit.height) or pixel_hash(image)!=unit.pixel_sha256:
        image.close();raise ValueError('Visual source integrity changed')
    return image


def _office_sources(extraction, issues):
    path=extraction.source_path
    placements=defaultdict(list)
    with ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):raise ValueError('Duplicate media package members')
        location_parts={}
        if extraction.file_type=='pptx':
            from pptx import Presentation
            location_parts={str(s.part.partname).lstrip('/'):n for n,s in enumerate(Presentation(path).slides,1)}
        segments={(s.part,s.paragraph_path):s.page_number for s in extraction.structure.segments} if extraction.structure else {}
        for relname in names:
            if not relname.endswith('.rels'):continue
            if relname=='_rels/.rels':part=''
            else:part=relname.replace('/_rels/','/')[:-5]
            image_rels=[]
            for rel in parse_xml(z.read(relname)):
                if not rel.get('Type','').endswith(('/image','/thumbnail')):continue
                if rel.get('TargetMode')=='External':issues['external_visual_media']+=1;continue
                target=posixpath.normpath(posixpath.join(posixpath.dirname(part),rel.get('Target',''))).lstrip('/')
                if target not in names:issues['missing_visual_media']+=1;continue
                image_rels.append((rel.get('Id'),target,rel.get('Type','').endswith('/thumbnail')))
            if not image_rels:continue
            root=parse_xml(z.read(part)) if part in names else None
            for rid,target,thumbnail in image_rels:
                if thumbnail:
                    placements[target].append(dict(location=1,part=part,relationship_id=rid,xml_path='',mapped=True,role='document_thumbnail'))
                    continue
                hits=[n for n in root.iter() if n.get(R+'embed')==rid or n.get(R+'id')==rid] if root is not None else []
                for node in hits:
                    location=location_parts.get(part)
                    ancestors=list(node.iterancestors())
                    if extraction.file_type=='docx':
                        paragraph=next((n for n in ancestors if n.tag=='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'),None)
                        location=segments.get((part,root.getroottree().getpath(paragraph))) if paragraph is not None else None
                    mapped=location is not None
                    if extraction.file_type=='pptx':
                        picture=next((n for n in ancestors if str(n.tag).endswith('}pic')),None)
                        if picture is None:mapped=False
                        for group in [n for n in ancestors if str(n.tag).endswith('}grpSp')]:
                            transform=group.find('{http://schemas.openxmlformats.org/presentationml/2006/main}grpSpPr/{http://schemas.openxmlformats.org/drawingml/2006/main}xfrm')
                            try:
                                for name in ('ext','chExt'):
                                    ext=transform.find('{http://schemas.openxmlformats.org/drawingml/2006/main}'+name)
                                    if int(ext.get('cx'))<=0 or int(ext.get('cy'))<=0:raise ValueError()
                            except Exception:mapped=False
                    if not mapped:issues['unmapped_visual_placement']+=1
                    placements[target].append(dict(location=location or 1,part=part,
                        relationship_id=rid,xml_path=root.getroottree().getpath(node),mapped=mapped))
        media=[n for n in names if n.startswith(('word/media/','ppt/media/')) or n.lower().startswith('docprops/thumbnail.')]
        for name in names:
            if name not in media and PurePosixPath(name).suffix.lower() in {'.png','.jpg','.jpeg','.gif','.svg','.wmf','.emf','.tif','.tiff'}:
                issues['uninspected_image_parts']+=1
        for name in names:
            if '/embeddings/' in name or '/activeX/' in name:issues['embedded_visual_objects']+=1
            if name.endswith('.xml') and ('/charts/' in name or '/diagrams/' in name):issues['charts_or_vector_content']+=1
        # Unsupported drawings are inventoried, never treated as face-free.
        for part in names:
            if not part.endswith('.xml') or not part.startswith(('word/','ppt/')):continue
            root=parse_xml(z.read(part))
            for node in root.iter():
                local=str(node.tag).split('}')[-1]
                if local in {'object','pict','graphicFrame','AlternateContent'}:issues['uninspected_visual_constructs']+=1
        for name in sorted(media):
            if PurePosixPath(name).suffix.lower() not in {'.png','.jpg','.jpeg'}:
                issues['unsupported_image_format']+=1;continue
            if z.getinfo(name).file_size>MAX_BYTES:issues['oversized_image']+=1;continue
            uses=placements[name]
            if not uses:
                issues['unmapped_visual_placement']+=1
                uses=[dict(location=1,part=name,xml_path='',mapped=False,role='package_media_not_mapped_to_page')]
            yield 'office_media',name,'display',uses,z.read(name)


def _pdf_sources(extraction,issues):
    with fitz.open(extraction.source_path) as doc:
        images=defaultdict(list)
        for p in extraction.pages:
            page=doc[p.page_number-1]
            if p.extraction_method=='ocr':
                dpi=extraction.pdf_source.ocr_dpi_by_page.get(str(p.page_number)) if extraction.pdf_source else None
                if type(dpi) is not int or not 72<=dpi<=600 or page.cropbox!=page.mediabox:
                    issues['unmapped_pdf_raster']+=1;continue
                # Use the exact established OCR raster frame/resolution; OCR not repeated.
                pix=page.get_pixmap(dpi=dpi,colorspace=fitz.csRGB,alpha=False,annots=False)
                yield 'pdf_raster',f'page:{p.page_number}:{dpi}','raw',[dict(location=p.page_number,dpi=dpi,mapped=True)],pix.tobytes('png')
            else:
                metadata={r[0]:r for r in page.get_images(full=True)}
                displayed=set()
                for item in page.get_image_info(xrefs=True):
                    xref=item.get('xref',0);transform=list(item['transform'])
                    if (not xref or xref not in metadata or metadata[xref][1]
                        or not all(isfinite(v) for v in transform)
                        or abs(transform[0]*transform[3]-transform[1]*transform[2])<1e-8):
                        issues['unmapped_pdf_image']+=1;continue
                    images[xref].append(dict(location=p.page_number,bbox=list(item['bbox']),transform=transform,mapped=True))
                    displayed.add(xref)
                if set(metadata)-displayed:issues['uninspected_pdf_image_resources']+=len(set(metadata)-displayed)
                if doc.xref_get_key(page.xref,'Thumb')[0]!='null':issues['uninspected_pdf_image_resources']+=1
                if page.get_drawings():issues['uninspected_pdf_vector_content']+=1
            if page.first_annot or page.first_widget or page.get_links():issues['uninspected_pdf_annotations']+=1
        if doc.embfile_count():issues['embedded_visual_objects']+=doc.embfile_count()
        for xref,uses in sorted(images.items()):
            yield 'pdf_image',f'xref:{xref}','raw',uses,doc.extract_image(xref)['image']


class VisualInspectionEngine:
    def __init__(self,detector=None):self.detector=detector

    def inspect(self,extraction):
        started=perf_counter();issues=Counter();result=VisualInspection(source_hash(extraction.source_path));cache={}
        if extraction.file_type=='image':
            sources=[('standalone_image','original','display',[dict(location=1,mapped=True)],Path(extraction.source_path).read_bytes())]
        else:
            sources=_pdf_sources(extraction,issues) if extraction.file_type=='pdf' else _office_sources(extraction,issues)
        for kind,ref,frame,uses,data in sources:
            try:
                image=decode(data,frame)
            except Exception:issues['image_decode_failed']+=1;continue
            with image:
                unit=VisualUnit(f'I{len(result.units)+1:06d}',kind,ref,sha256(data).hexdigest(),pixel_hash(image),
                    image.width,image.height,frame,sorted({u['location'] for u in uses}),uses,all(u['mapped'] for u in uses))
                result.units.append(unit)
                key=(unit.image_sha256,frame)
                if key in cache:boxes=cache[key];result.cache_hits+=1
                else:
                    if self.detector is None:self.detector=FaceDetector()
                    boxes=self.detector.detect(encode(image));cache[key]=boxes
                for box,score in boxes:
                    decision='CONFIRM' if score>=result.confirm_threshold and unit.mapped else 'REVIEW'
                    result.faces.append(FaceDetection(f'V{len(result.faces)+1:06d}',unit.unit_id,list(box),score,
                        extraction.file_type,unit.locations[0],unit.locations,unit.source_ref,final_decision=decision,
                        validation_decision=decision,validation_reason='mapped_face_privacy_policy' if decision=='CONFIRM'
                        else 'face_confidence_or_mapping_requires_review'))
        result.unsupported=dict(sorted(issues.items()));result.detection_seconds=perf_counter()-started
        return result.validate()
