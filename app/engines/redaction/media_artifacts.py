"""Destructively mask mapped OCR blocks while preserving unrelated image pixels."""
from collections import defaultdict
from hashlib import sha256
from math import floor, ceil, isfinite
from pathlib import Path
from zipfile import ZipFile
from PIL import ImageDraw
from app.engines.visual_detection.images import decode, encode, pixel_hash


def media_plans(extraction, redaction, face_members=None):
    records = defaultdict(list)
    for record in redaction.redactions:
        records[record.page_number].append(record)
    plans = {}
    with ZipFile(extraction.source_path) as archive:
        for page in extraction.pages:
            if page.extraction_method != 'media_ocr':
                continue
            source = page.media_source
            if not source or '\n'.join(b.text for b in page.blocks or []) != page.text:
                raise ValueError('Embedded OCR source mapping differs')
            data = archive.read(source['part'])
            if sha256(data).hexdigest() != source['sha256']:
                raise ValueError('Embedded OCR source changed')
            selected = records[page.page_number]
            if not selected:
                continue
            with decode((face_members or {}).get(source['part'], data), 'display') as image:
                if image.size != (source['width'], source['height']):
                    raise ValueError('Embedded image dimensions changed')
                draw = ImageDraw.Draw(image)
                spans, cursor = [], 0
                for block in page.blocks:
                    spans.append((cursor, cursor + len(block.text), block))
                    cursor += len(block.text) + 1
                for record in selected:
                    hits = [(start,end,b) for start,end,b in spans
                            if start < record.original_end and record.original_start < end]
                    covered = ''.join(page.text[max(start,record.original_start):min(end,record.original_end)]
                                      for start,end,_ in hits)
                    if not hits or ''.join(covered.split()) != ''.join(record.original_text.split()):
                        raise ValueError('Embedded OCR record offsets differ')
                    for _,_,block in hits:
                        points = block.bounding_box
                        if len(points) != 4 or any(len(p)!=2 or any(not isinstance(v,(float,int)) or not isfinite(v) for v in p) for p in points):
                            raise ValueError('Invalid embedded OCR coordinates')
                        box = (floor(min(p[0] for p in points)), floor(min(p[1] for p in points)),
                               ceil(max(p[0] for p in points)), ceil(max(p[1] for p in points)))
                        if not (0 <= box[0] < box[2] <= image.width and 0 <= box[1] < box[3] <= image.height):
                            raise ValueError('Embedded OCR box outside source image')
                        draw.rectangle(box, fill='black')
                payload = encode(image, Path(source['part']).suffix)
            with decode(payload, 'raw') as rendered:
                plans[source['part']] = (payload, pixel_hash(rendered))
    return plans


def verify_media(extraction, redaction, result):
    from .visual_artifacts import prepare_visual
    expected = type(result)()
    faces = {u.source_ref: data for u,data,_ in prepare_visual(extraction, expected).values()}
    plans = media_plans(extraction, redaction, faces)
    with ZipFile(result.path) as archive:
        for part,(payload,digest) in plans.items():
            data = archive.read(part)
            with decode(data, 'raw') as image:
                if sha256(data).hexdigest() != sha256(payload).hexdigest() or pixel_hash(image) != digest:
                    raise ValueError('Serialized embedded OCR mask differs')
    return plans


def update_face_checks(plans, media):
    for unit,_,check in plans.values():
        if unit.kind == 'office_media' and unit.source_ref in media:
            payload,digest = media[unit.source_ref]
            check['expected_sha256'] = sha256(payload).hexdigest()
            check['pixel_sha256'] = digest
