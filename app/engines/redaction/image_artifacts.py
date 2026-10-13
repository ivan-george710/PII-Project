"""Standalone image artifacts: compose face blur and destructive OCR masks."""
from copy import deepcopy
from hashlib import sha256
from math import floor, ceil
from pathlib import Path
from uuid import uuid4
from PIL import ImageDraw
from app.engines.visual_detection.images import decode, encode, pixel_hash
from app.engines.extraction.office import source_hash
from .artifacts import ArtifactResult
from .visual_artifacts import prepare_visual, verify_visual


def composed_image(extraction, redaction, plans):
    image = decode(Path(extraction.source_path).read_bytes(), 'display')
    for unit,data,_ in plans.values():
        if unit.kind == 'standalone_image':
            image.close(); image=decode(data,'raw')
    page=extraction.pages[0]
    if '\n'.join(b.text for b in page.blocks or []) != page.text:
        image.close(); raise ValueError('Image OCR mapping differs')
    spans=[];cursor=0
    for block in page.blocks or []:
        spans.append((cursor,cursor+len(block.text),block));cursor+=len(block.text)+1
    draw=ImageDraw.Draw(image)
    for record in redaction.redactions:
        hits=[b for start,end,b in spans if start<record.original_end and record.original_start<end]
        if not hits:image.close();raise ValueError('Image redaction has no mapped block')
        for block in hits:
            points=block.bounding_box
            box=(floor(min(p[0] for p in points)),floor(min(p[1] for p in points)),
                 ceil(max(p[0] for p in points)),ceil(max(p[1] for p in points)))
            if not 0<=box[0]<box[2]<=image.width or not 0<=box[1]<box[3]<=image.height:
                image.close();raise ValueError('Image OCR box is outside raster')
            draw.rectangle(box,fill='black')
    return image


class ImageArtifactEngine:
    def __init__(self, output_dir=None):
        self.output_dir=Path(output_dir or '.private_artifacts')

    def redact(self, extraction, detection, redaction):
        from app.engines.audit.storage import AuditStore
        result=ArtifactResult(format='image',source_sha256=source_hash(extraction.source_path),
                              known_review_complete=redaction.redaction_complete)
        plans=prepare_visual(extraction,result)
        with composed_image(extraction,redaction,plans) as image:
            data=encode(image)
        for unit,_,check in plans.values():
            with decode(data,'raw') as image:
                check['pixel_sha256']=pixel_hash(image)
                check['expected_sha256']=sha256(data).hexdigest()
        store=AuditStore(self.output_dir);store._prepare()
        result.path=store.directory/('review_'+uuid4().hex+'.png')
        result.path.write_bytes(data);result.path.chmod(0o600)
        result.redaction_completed=True;result.applied_redactions=len(redaction.redactions)
        return result

    def verify(self, extraction, redaction, result):
        checked=deepcopy(result);checked.verification_completed=True
        try:
            if source_hash(extraction.source_path)!=checked.source_sha256:raise ValueError('Image source changed')
            expected=ArtifactResult();plans=prepare_visual(extraction,expected)
            with composed_image(extraction,redaction,plans) as image, decode(checked.path.read_bytes(),'raw') as actual:
                if pixel_hash(image)!=pixel_hash(actual):raise ValueError('Image mask differs')
            checked.reopened=True;checked.page_count_preserved=True;checked.supported_content_verified=True
        except Exception:
            checked.verification_failures+=1
        return verify_visual(extraction,checked,redaction)
