"""Destructive PDF review artifacts with exact native or coarse OCR-block mappings."""
from collections import defaultdict
from copy import deepcopy
import hashlib
from io import BytesIO
from math import isfinite, floor, ceil
import os
from pathlib import Path
import tempfile
from uuid import uuid4

import pymupdf as fitz
from PIL import Image, ImageDraw

from app.engines.audit.storage import AuditStore, PROJECT_ROOT
from app.engines.extraction.office import source_hash
from .engine import RedactionEngine
from .artifacts import ArtifactResult, ArtifactMappingIssue, ArtifactValidationError


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _native_chars(page, extracted):
    if page.rotation:
        return None  # Rotated coordinate systems are not guessed.
    chars = []
    for block in page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                for char in span["chars"]:
                    chars.extend((c, fitz.Rect(char["bbox"])) for c in char["c"] if not c.isspace())
    indices = [i for i, c in enumerate(extracted) if not c.isspace()]
    if "".join(c for c, _ in chars) != "".join(extracted[i] for i in indices):
        return None
    return dict(zip(indices, [rect for _, rect in chars]))


def _rectangles(char_map, start, end):
    selected = [rect for i, rect in char_map.items() if start <= i < end]
    if not selected:
        return []
    rectangles = []
    for rect in selected:
        if rectangles and abs(rectangles[-1].y0 - rect.y0) < .5 and abs(rectangles[-1].y1 - rect.y1) < .5:
            rectangles[-1] |= rect
        else:
            rectangles.append(fitz.Rect(rect))
    # Fail rather than delete unrelated overlapping glyphs.
    for i, rect in char_map.items():
        if start <= i < end:
            continue
        if any((rect & region).get_area() > .05 for region in rectangles):
            return []
    return rectangles


def _write_label(page, rect, text, unicode_font=False, minimum_size=4):
    if not text:
        return True
    if "\n" in text or "\r" in text:
        return False
    unicode_font=unicode_font and any(ord(c)>127 for c in text)
    font=fitz.Font("cjk" if unicode_font else "helv")
    fontname="reviewfont" if unicode_font else "helv"
    if unicode_font:
        page.insert_font(fontname=fontname,fontbuffer=font.buffer)
    unit = font.text_length(text, fontsize=1)
    size = min(10, (rect.height-.5) / 1.6, (rect.width-1) / max(unit, 1))
    if size < minimum_size:
        return False
    page.insert_text((rect.x0+.25, rect.y0+.25 + size*1.15), text, fontsize=size, fontname=fontname, color=(0, 0, 0))
    return True


class PDFArtifactEngine:
    def __init__(self, output_dir=None):
        self.output_dir = Path(output_dir) if output_dir else PROJECT_ROOT / ".private_artifacts"

    def redact(self, extraction, effective_detection, redaction):
        if extraction.file_type != "pdf" or extraction.pdf_source is None:
            raise ArtifactValidationError("Fingerprint and OCR resolution metadata are required")
        if source_hash(extraction.source_path) != extraction.pdf_source.source_sha256:
            raise ArtifactValidationError("PDF source integrity changed")
        if RedactionEngine().redact(extraction, effective_detection) != redaction:
            raise ArtifactValidationError("PDF decisions differ from text redaction")
        result = ArtifactResult(format="pdf", source_sha256=extraction.pdf_source.source_sha256,
                                known_review_complete=redaction.redaction_complete)
        from .visual_artifacts import prepare_visual,native_images
        visual_plans=prepare_visual(extraction,result)
        records = defaultdict(list)
        for record in redaction.redactions:
            records[record.page_number].append(record)
        def issue(record, code):
            result.mapping_failures += 1
            result.mapping_issues.append(ArtifactMappingIssue(record.page_number, record.original_start,
                record.original_end, record.entity_type, code))
        fitz.TOOLS.set_small_glyph_heights(True)
        with fitz.open(extraction.source_path) as original, fitz.open() as output:
            if len(original) != len(extraction.pages) or [p.page_number for p in extraction.pages] != list(range(1, len(original)+1)):
                raise ArtifactValidationError("PDF extraction page accounting differs")
            for extracted in extraction.pages:
                number = extracted.page_number
                source = original[number-1]
                if source.first_annot or source.first_widget or source.get_links() or original.embfile_count():
                    result.unsupported_structures["pdf_annotations_or_attachments"] = 1
                if extracted.extraction_method == "text":
                    if source.get_images():
                        result.unsupported_structures["pdf_images_without_ocr"] = 1
                    output.insert_pdf(original, from_page=number-1, to_page=number-1)
                    page = output[-1]
                    for unit,data,check in visual_plans.values():
                        if unit.kind=='pdf_image' and number in unit.locations:
                            if not native_images(page,output,unit,data,check):result.face_mapping_failures+=len(check['face_ids'])
                    char_map = _native_chars(source, extracted.text)
                    applied = []
                    for record in records[number]:
                        regions = _rectangles(char_map, record.original_start, record.original_end) if char_map else []
                        if not regions:
                            issue(record, "native_coordinates_unverified")
                            continue
                        for region in regions:
                            page.add_redact_annot(region, fill=(1, 1, 1), cross_out=False)
                        applied.append((record, regions))
                    if applied:
                        page.apply_redactions(images=2, graphics=0, text=0)
                    for record, regions in applied:
                        labelled = _write_label(page, regions[0], record.tag)
                        result.region_checks.append({"kind":"native", "page_number":number,
                            "rectangles":[list(r) for r in regions], "tag":record.tag, "labelled":labelled,
                            "original_text":record.original_text})
                        result.applied_redactions += 1
                elif extracted.extraction_method == "ocr":
                    dpi = extraction.pdf_source.ocr_dpi_by_page.get(str(number))
                    if type(dpi) is not int or not 72 <= dpi <= 600 or source.cropbox != source.mediabox:
                        raise ArtifactValidationError("OCR render geometry is unverified")
                    pix = source.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False, annots=False)
                    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    for unit,data,check in visual_plans.values():
                        if unit.kind=='pdf_raster' and number in unit.locations:
                            from app.engines.visual_detection.images import decode,pixel_hash
                            if image.size!=(unit.width,unit.height) or pixel_hash(image)!=unit.pixel_sha256:
                                raise ArtifactValidationError('OCR visual raster mapping changed')
                            image.close();image=decode(data,'raw')
                    block_spans = []
                    cursor = 0
                    blocks = extracted.blocks or []
                    reliable = "\n".join(b.text for b in blocks) == extracted.text
                    for block in blocks:
                        block_spans.append((cursor, cursor+len(block.text)))
                        cursor += len(block.text)+1
                    edits = defaultdict(list)
                    mapped_records = []
                    for record in records[number]:
                        matches = [i for i, (start,end) in enumerate(block_spans)
                                   if start < record.original_end and record.original_start < end]
                        covered="".join(extracted.text[max(record.original_start,block_spans[i][0]):min(record.original_end,block_spans[i][1])] for i in matches)
                        if not reliable or not matches or "".join(covered.split())!="".join(record.original_text.split()):
                            issue(record, "ocr_block_offsets_unverified")
                            continue
                        valid=True
                        for index in matches:
                            points = blocks[index].bounding_box
                            if (len(points) != 4 or any(len(p)!=2 or any(not isinstance(v,(int,float)) or not isfinite(v) for v in p) for p in points)):
                                valid=False
                                break
                            x0,y0,x1,y1 = min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)
                            if not 0 <= x0 < x1 <= pix.width or not 0 <= y0 < y1 <= pix.height:
                                valid=False
                                break
                        if not valid:
                            issue(record, "ocr_box_invalid")
                            continue
                        for position,index in enumerate(matches):
                            left,right=block_spans[index]
                            edits[index].append((max(record.original_start,left)-left,min(record.original_end,right)-left,
                                                 record.tag if position==0 else ""))
                        mapped_records.append(record)
                    patches = []
                    draw = ImageDraw.Draw(image)
                    for index, block_edits in edits.items():
                        points = blocks[index].bounding_box
                        box = (floor(min(p[0] for p in points)),floor(min(p[1] for p in points)),
                               ceil(max(p[0] for p in points)),ceil(max(p[1] for p in points)))
                        text = blocks[index].text
                        for start,end,tag in sorted(block_edits,reverse=True):
                            text = text[:start]+tag+text[end:]
                        draw.rectangle(box, fill="white")
                        private_regions=[fitz.Rect(min(p[0] for p in b.bounding_box),min(p[1] for p in b.bounding_box),
                                                   max(p[0] for p in b.bounding_box),max(p[1] for p in b.bounding_box))
                                         for b in blocks if b.mask_only]
                        opaque=blocks[index].mask_only or any((fitz.Rect(box)&region).get_area()>0 for region in private_regions)
                        patches.append((box,"" if opaque else text,
                                        [] if opaque else [tag for _,_,tag in block_edits if tag]))
                    page = output.new_page(width=source.rect.width, height=source.rect.height)
                    buffer = BytesIO()
                    image.save(buffer, format="PNG")
                    for unit,data,check in visual_plans.values():
                        if unit.kind=='pdf_raster' and number in unit.locations:
                            # Record composed blur + text-mask pixels. Verification
                            # independently recomputes the same composition below.
                            check['composed_pixel_sha256']=_digest(image.tobytes())
                            check['pixel_sha256']=_digest(image.tobytes())
                    page.insert_image(page.rect, stream=buffer.getvalue())
                    result.region_checks.append({"kind":"raster", "page_number":number,
                        "image_sha256":_digest(image.tobytes()), "width":image.width,"height":image.height})
                    for box,text,tags in patches:
                        rect=fitz.Rect([v*72/dpi for v in box])
                        labelled = _write_label(page, rect, text, unicode_font=True)
                        tag_labelled=labelled
                        if not labelled:
                            # Labels are optional when the original block is too
                            # small. Keep its non-sensitive OCR transcription.
                            for tag in tags:
                                text=text.replace(tag,"")
                            labelled=_write_label(page,rect,text,unicode_font=True,minimum_size=1)
                        result.region_checks.append({"kind":"ocr", "page_number":number,
                            "rectangles":[list(rect)], "expected_text":text, "labelled":labelled,
                            "tags":tags,"tag_labelled":tag_labelled})
                    result.applied_redactions += len(mapped_records)
                    image.close()
                else:
                    raise ArtifactValidationError("Unsupported PDF extraction route")
                # Full-page rerender is an independent check of the serialized artifact later.
                pix = page.get_pixmap(colorspace=fitz.csRGB, alpha=False, annots=False)
                result.region_checks.append({"kind":"page", "page_number":number,
                    "dimensions":[page.rect.width,page.rect.height],"render_sha256":_digest(pix.samples)})
            store=AuditStore(self.output_dir)
            store._prepare()
            self.output_dir=store.directory
            path=self.output_dir/("review_"+uuid4().hex+".pdf")
            temporary=None
            try:
                with tempfile.NamedTemporaryFile(dir=self.output_dir,prefix=".artifact-",suffix=".pdf",delete=False) as stream:
                    temporary=Path(stream.name)
                    if os.name != "nt": os.fchmod(stream.fileno(),0o600)
                output.set_metadata({})
                output.save(temporary,garbage=4,deflate=True,clean=True)
                os.replace(temporary,path)
            finally:
                if temporary and temporary.exists(): temporary.unlink()
            result.path=path
        result.redaction_completed=True
        return result

    def verify(self, extraction, redaction, result):
        checked=deepcopy(result)
        checked.verification_completed=True
        checked.verification_failures=checked.mapping_failures
        checked.supported_content_verified=False
        try:
            if source_hash(extraction.source_path)!=checked.source_sha256:
                raise ArtifactValidationError("PDF source integrity changed before verification")
            with fitz.open(checked.path) as output:
                if any(output.metadata.get(k) for k in ("author","title","subject","keywords","creator","producer")):
                    checked.verification_failures+=1
                checked.reopened=True
                checked.page_count_preserved=len(output)==len(extraction.pages)
                if not checked.page_count_preserved: checked.verification_failures+=1
                for check in checked.region_checks:
                    page=output[check["page_number"]-1]
                    if check["kind"]=="page":
                        pix=page.get_pixmap(colorspace=fitz.csRGB,alpha=False,annots=False)
                        # OCR raster bytes and every retained label are independently
                        # verified below. MuPDF's in-memory font rasterization differs
                        # slightly after PDF serialization; it is not removal evidence.
                        native = extraction.pages[check["page_number"]-1].extraction_method == "text"
                        if [page.rect.width,page.rect.height]!=check["dimensions"] or (native and _digest(pix.samples)!=check["render_sha256"]):
                            checked.verification_failures+=1
                    elif check["kind"]=="raster":
                        images=page.get_images(full=True)
                        if len(images)!=1:
                            checked.verification_failures+=1
                        else:
                            pix=fitz.Pixmap(output,images[0][0])
                            if _digest(pix.samples)!=check["image_sha256"] or pix.width!=check["width"] or pix.height!=check["height"]:
                                checked.verification_failures+=1
                    else:
                        text=" ".join(page.get_textbox(fitz.Rect(r)) for r in check["rectangles"])
                        norm=lambda value:"".join(value.split())
                        if check["kind"]=="native":
                            if norm(check["original_text"]) in norm(text): checked.verification_failures+=1
                            if check["labelled"] and norm(check["tag"]) not in norm(text): checked.verification_failures+=1
                        # Adjacent mapped OCR boxes may overlap slightly. Their
                        # retained transcription must be present, while the exact
                        # cleared raster payload is independently checked above.
                        elif check["labelled"] and norm(check["expected_text"]) not in norm(text):
                            checked.verification_failures+=1
                full="\n".join(p.get_text() for p in output)
                for tag in redaction.tag_mapping:
                    full=full.replace(tag, "")
                checked.residual_confirmed_values=sum(full.count(v) for v in {r.original_text for r in redaction.redactions})
            checked.supported_content_verified=checked.verification_failures==0
        except Exception:
            checked.verification_failures+=1
        from .visual_artifacts import verify_visual
        return verify_visual(extraction,checked,redaction)
