from __future__ import annotations

from collections.abc import Iterable
from hashlib import sha256
from io import BytesIO
from math import isfinite
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID
import os
import re

import pymupdf
from PIL import Image
from pypdf import PdfReader
from pypdf.generic import ArrayObject, ContentStream, NameObject, NullObject

from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.models import ExtractedTextBlock, SanitizedArtifact, SourceLocation
from pii_guard.redaction.image import MAX_IMAGE_PIXELS, _encode_image, _paint_image, _pixel_box, _source_key, _validate_regions
from pii_guard.rules.policy import RedactionTarget
from pii_guard.redaction.metadata import strip_pdf_metadata, validate_pdf_metadata


_BASE_FONTS = {
    "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique",
    "Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic",
    "Courier", "Courier-Bold", "Courier-Oblique", "Courier-BoldOblique", "Symbol", "ZapfDingbats",
}
_OPERATORS = set(b"q Q cm BT ET Tf Tj TJ Td TD Tm T* Tc Tw Tz TL Tr Ts ' \" g G rg RG k K w J j M d ri i m l c v y h re S s f F f* B B* b b* n Do".split())


def _keys(value, allowed: set[str]) -> None:
    if set(value) - allowed:
        raise ValueError("Unsupported PDF structure")


def _resources(resources) -> None:
    resources = resources.get_object() if hasattr(resources, "get_object") else resources
    _keys(resources, {"/Font", "/XObject", "/ProcSet"})
    if any(value not in {"/PDF", "/Text", "/ImageB", "/ImageC", "/ImageI"}
           for value in resources.get("/ProcSet", [])):
        raise ValueError("Unsupported resource data")
    fonts = resources.get("/Font", {})
    fonts = fonts.get_object() if hasattr(fonts, "get_object") else fonts
    for resource_name, font in fonts.items():
        font = font.get_object()
        _keys(font, {"/Type", "/Subtype", "/BaseFont", "/Encoding", "/Name"})
        if font.get("/Subtype") != "/Type1" or str(font.get("/BaseFont", ""))[1:] not in _BASE_FONTS:
            raise ValueError("Unsupported PDF font")
        if font.get("/Encoding", "/WinAnsiEncoding") not in {"/WinAnsiEncoding", "/MacRomanEncoding"}:
            raise ValueError("Unsupported font encoding")
        if '/Name' in font and (not isinstance(font['/Name'], NameObject) or font['/Name'] != resource_name):
            raise ValueError('Unsupported font name payload')
    images = resources.get("/XObject", {})
    images = images.get_object() if hasattr(images, "get_object") else images
    for image in images.values():
        image = image.get_object()
        _keys(image, {"/Type", "/Subtype", "/Width", "/Height", "/ColorSpace",
                      "/BitsPerComponent", "/Filter", "/DecodeParms", "/Length"})
        if image.get("/Subtype") != "/Image" or image.get("/ColorSpace") not in {"/DeviceRGB", "/DeviceGray"}:
            raise ValueError("Unsupported image or Form XObject")
        if image.get("/BitsPerComponent") != 8:
            raise ValueError("Unsupported image precision")
        filters = image.get("/Filter", [])
        filters = filters if isinstance(filters, list) else [filters]
        if any(f not in {"/FlateDecode", "/DCTDecode", "/ASCII85Decode"} for f in filters):
            raise ValueError("Unsupported image filter")
        if image.get("/DecodeParms"):
            _keys(image["/DecodeParms"], {"/Predictor", "/Columns", "/Colors", "/BitsPerComponent"})


def _inspect_structure(reader: PdfReader) -> None:
    if reader.is_encrypted or not 0 < len(reader.pages) <= 100:
        raise ValueError("Encrypted or oversized PDF")
    _keys(reader.trailer, {"/Root", "/Info", "/ID", "/Size", "/Prev", "/XRefStm"})
    validate_pdf_metadata(reader)
    root = reader.trailer["/Root"]
    _keys(root, {"/Type", "/Pages", "/Version", "/PageMode", "/PageLayout", "/Metadata"})
    if not isinstance(root.get('/Type'), NameObject) or root['/Type'] != '/Catalog':
        raise ValueError('Invalid PDF catalog type')
    structural_names = {
        '/Version': {f'/1.{minor}' for minor in range(8)} | {'/2.0'},
        '/PageMode': {'/UseNone', '/UseOutlines', '/UseThumbs', '/FullScreen', '/UseOC', '/UseAttachments'},
        '/PageLayout': {'/SinglePage', '/OneColumn', '/TwoColumnLeft', '/TwoColumnRight', '/TwoPageLeft', '/TwoPageRight'},
    }
    for key, names in structural_names.items():
        if key in root and (not isinstance(root[key], NameObject) or root[key] not in names):
            raise ValueError('Unsupported catalog preference payload')
    seen = set()

    def inspect_tree(node):
        node = node.get_object()
        if id(node) in seen:
            raise ValueError("Invalid PDF page tree")
        seen.add(id(node))
        if node.get("/Type") == "/Pages":
            _keys(node, {"/Type", "/Kids", "/Count", "/Parent", "/MediaBox", "/CropBox", "/Rotate", "/Resources"})
            if "/Resources" in node:
                _resources(node["/Resources"])
            for child in node["/Kids"]:
                inspect_tree(child)
        elif node.get("/Type") != "/Page":
            raise ValueError("Invalid page node")

    inspect_tree(root["/Pages"])
    for page in reader.pages:
        _keys(page, {"/Type", "/Parent", "/MediaBox", "/CropBox", "/Rotate", "/Resources", "/Contents",
                     "/BleedBox", "/TrimBox", "/ArtBox", "/Trans", "/Annots", "/Metadata"})
        if "/Annots" in page:
            annotations = page["/Annots"]
            if not isinstance(annotations, (ArrayObject, NullObject)) or (isinstance(annotations, ArrayObject) and annotations):
                raise ValueError("Unsupported annotations")
        if page.get("/Trans"):
            raise ValueError("Unsupported page transition")
        if tuple(page.mediabox.lower_left) != (0, 0):
            raise ValueError("Unsupported nonzero media-box origin")
        if int(page.get("/Rotate", 0)) not in {0, 90, 180, 270}:
            raise ValueError("Unsupported rotation")
        _resources(page.get("/Resources", {}))
        content = page.get("/Contents")
        streams = content.get_object() if content is not None else []
        streams = streams if isinstance(streams, list) else [streams]
        for stream in streams:
            _keys(stream.get_object(), {"/Length", "/Filter", "/DecodeParms"})
        operations = ContentStream(content, reader).operations if content is not None else []
        for operands, operator in operations:
            if operator not in _OPERATORS:
                raise ValueError("Unsupported PDF drawing operation")
            if operator in {b"Tr", b"Ts"} and (len(operands) != 1 or operands[0] != 0):
                raise ValueError("Unsupported hidden or shifted text")


def _visible_rect(page) -> pymupdf.Rect:
    return page.rect * page.derotation_matrix


def _valid_rect(rect, page) -> pymupdf.Rect:
    rect = pymupdf.Rect(rect)
    visible = _visible_rect(page)
    if not all(isfinite(v) for v in rect) or rect.is_empty or rect.is_infinite:
        raise ValueError("Invalid page geometry")
    tolerance = pymupdf.Rect(visible.x0 - 0.01, visible.y0 - 0.01, visible.x1 + 0.01, visible.y1 + 0.01)
    if not tolerance.contains(rect):
        raise ValueError("Content outside visible crop box")
    return rect


def _native_map(page, text: str) -> dict[int, pymupdf.Rect]:
    chars = []
    raw = page.get_text("rawdict", flags=pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_PRESERVE_LIGATURES)
    for block in raw["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                for char in span["chars"]:
                    if len(char["c"]) != 1:
                        raise ValueError("Ambiguous glyph encoding")
                    if not char["c"].isspace():
                        chars.append((char["c"], _valid_rect(char["bbox"], page)))
    indices = [index for index, char in enumerate(text) if not char.isspace()]
    if "".join(char for char, _ in chars) != "".join(text[index] for index in indices):
        raise ValueError("Native text cannot be aligned with glyph geometry")
    return dict(zip(indices, (rect for _, rect in chars), strict=True))


def redact_pdf(data: bytes, targets: Iterable[RedactionTarget] = (), *, artifact_id: UUID,
               blocks: Iterable[ExtractedTextBlock] = (), region_sources: Iterable[SourceLocation] = (),
               submission_id: UUID | None = None) -> bytes:
    """Permanently redact a supported PDF without rasterizing its pages.

    Original extracted blocks bind offsets/boxes to this artifact. Future FACE
    locations use the rendered-page frame and must be supplied as region_sources.
    Returns bytes only after the complete rewrite succeeds; no partial files exist.
    """
    try:
        if not isinstance(data, bytes) or len(data) > 25 * 1024 * 1024 or not isinstance(artifact_id, UUID):
            raise ValueError("Invalid PDF input")
        reader = PdfReader(BytesIO(data), strict=True)
        _inspect_structure(reader)
        known = {}
        region_locations = []
        for block in blocks:
            if not isinstance(block, ExtractedTextBlock):
                raise ValueError("Invalid extraction contract")
            block = ExtractedTextBlock.model_validate(block.model_dump(warnings=False))
            loc = block.location
            if loc.artifact_id != artifact_id or loc.slide_number is not None or not loc.page_number or loc.page_number > len(reader.pages):
                raise ValueError("Invalid PDF extraction source")
            prefix = f"pdf:page:{loc.page_number}"
            if loc.kind == "native_text":
                if loc.source_ref != f"{prefix}:native_text" or loc.bbox is not None:
                    raise ValueError("Invalid native text reference")
                if block.text != (reader.pages[loc.page_number - 1].extract_text() or ""):
                    raise ValueError("Original native text changed")
            elif not re.fullmatch(re.escape(prefix) + r":rendered:ocr:[0-9]+", loc.source_ref):
                raise ValueError("Invalid OCR source reference")
            key = _source_key(loc)
            if key in known and known[key] != block:
                raise ValueError("Conflicting original blocks")
            known[key] = block
            if loc.kind == "ocr":
                region_locations.append(loc)
        for source in region_sources:
            source = SourceLocation.model_validate(source.model_dump(warnings=False))
            if source.kind != "face" or source.slide_number is not None or not source.page_number or source.page_number > len(reader.pages):
                raise ValueError("Invalid face source")
            if source.source_ref != f"pdf:page:{source.page_number}:rendered":
                raise ValueError("Invalid rendered face reference")
            region_locations.append(source)
        validated_targets = []
        region_targets = []
        for target in targets:
            if not isinstance(target, RedactionTarget):
                raise ValueError("Expected enabled redaction target")
            target = RedactionTarget.model_validate(target.model_dump(warnings=False))
            loc = target.location
            if loc.artifact_id != artifact_id or loc.slide_number is not None or not loc.page_number or loc.page_number > len(reader.pages):
                raise ValueError("Target page or artifact mismatch")
            if loc.kind == "native_text":
                block = known.get(_source_key(loc))
                if block is None or loc.bbox is not None or not 0 <= loc.start < loc.end <= len(block.text):
                    raise ValueError("Native target source mismatch")
            else:
                region_targets.append(target)
            validated_targets.append(target)
        _validate_regions(region_targets, region_locations, artifact_id)

        with pymupdf.open(stream=data, filetype="pdf") as document:
            if document.is_repaired or document.page_count != len(reader.pages):
                raise ValueError("Unreliable PDF parsing")
            plans = {index: [] for index in range(document.page_count)}
            native_maps = {}
            for target in validated_targets:
                loc = target.location
                index = loc.page_number - 1
                page = document[index]
                if loc.kind == "native_text":
                    if index not in native_maps:
                        native_maps[index] = _native_map(page, known[_source_key(loc)].text)
                    rects = [native_maps[index][position] for position in range(loc.start, loc.end)
                             if position in native_maps[index]]
                    if not rects:
                        raise ValueError("Native span has no reliable glyph geometry")
                    plans[index].extend(rects)
                else:
                    x, y, w, h = loc.bbox
                    display = page.rect
                    rect = pymupdf.Rect(x * display.width, y * display.height,
                                        (x + w) * display.width, (y + h) * display.height)
                    plans[index].append(_valid_rect(rect * page.derotation_matrix, page))

            # Validate every image placement before modifying the document. Shared,
            # transformed and hidden images are deliberately unsupported for now.
            images = []
            seen_images = set()
            for index, page in enumerate(document):
                for trace in page.get_texttrace():
                    if trace["type"] != 0:
                        raise ValueError("Invisible or unsupported PDF text")
                    _valid_rect(trace["bbox"], page)
                placed = set()
                for info in page.get_image_info(xrefs=True):
                    xref = info["xref"]
                    a, b, c, d, _, _ = info["transform"]
                    if not xref or xref in seen_images or b != 0 or c != 0 or a <= 0 or d <= 0:
                        raise ValueError("Shared or transformed PDF image")
                    if info["width"] * info["height"] > MAX_IMAGE_PIXELS:
                        raise ValueError("PDF image exceeds pixel limit")
                    placement = _valid_rect(info["bbox"], page)
                    pixel_boxes = []
                    for rect in plans[index]:
                        overlap = placement & rect
                        if not overlap.is_empty:
                            box = ((overlap.x0 - placement.x0) / placement.width,
                                   (overlap.y0 - placement.y0) / placement.height,
                                   overlap.width / placement.width, overlap.height / placement.height)
                            pixel_boxes.append(_pixel_box(box, info["width"], info["height"]))
                    images.append((index, xref, pixel_boxes))
                    placed.add(xref)
                    seen_images.add(xref)
                if {item[0] for item in page.get_images(full=True)} != placed:
                    raise ValueError("Unused or hidden PDF image resources")

            # Rebuild all image rasters, removing metadata and the old payloads.
            # Redaction masks are painted into source pixels, not just page overlays.
            for index, xref, pixel_boxes in images:
                image_data = document.extract_image(xref)["image"]
                with Image.open(BytesIO(image_data)) as image:
                    image.load()
                    with _paint_image(image, pixel_boxes) as painted:
                        encoded = _encode_image(painted, "PNG")
                document[index].replace_image(xref, stream=encoded)
            for index, rects in plans.items():
                page = document[index]
                # MuPDF's fill placement can shift on cropped/rotated pages.
                # Apply in an unrotated full-media frame, translating the planned
                # crop-relative geometry, then restore the original display boxes.
                crop, rotation = pymupdf.Rect(page.cropbox), page.rotation
                if rects:
                    page.set_rotation(0)
                    page.set_cropbox(page.mediabox)
                offset = crop.tl - page.cropbox.tl
                for rect in sorted({tuple(rect) for rect in rects}):
                    moved = pymupdf.Rect(rect)
                    moved.x0 += offset.x
                    moved.x1 += offset.x
                    moved.y0 += offset.y
                    moved.y1 += offset.y
                    page.add_redact_annot(moved, fill=(0, 0, 0), cross_out=False)
                if rects and not page.apply_redactions(images=0, graphics=2, text=0):
                    raise ValueError("PDF content redaction did not complete")
                if rects:
                    page.set_cropbox(crop)
                    page.set_rotation(rotation)
            # Remove root/page XMP and identifiers as well as scalar Info. Fresh
            # garbage collection removes obsolete metadata objects and streams.
            strip_pdf_metadata(document)
            output = document.tobytes(garbage=4, clean=True, deflate=True, incremental=False)
            reopened = PdfReader(BytesIO(output), strict=True)
            validate_pdf_metadata(reopened)
            owners = [reopened.trailer['/Root'], *reopened.pages]
            if reopened.metadata or any('/Metadata' in owner and not isinstance(owner['/Metadata'], NullObject) for owner in owners):
                raise ValueError('PDF metadata survived rewriting')
            with pymupdf.open(stream=output, filetype='pdf') as checked:
                if checked.is_repaired or checked.page_count != document.page_count or checked.get_xml_metadata():
                    raise ValueError('Invalid sanitized PDF')
            return output
    except Exception:
        raise ProcessingError(ProcessingErrorCode.REDACTION_FAILED,
            "PDF redaction failed: unsupported structure or unreliable source geometry.",
            submission_id=submission_id if isinstance(submission_id, UUID) else None,
            artifact_id=artifact_id if isinstance(artifact_id, UUID) else None) from None


def redact_pdf_file(source_path: Path, output_path: Path, targets: Iterable[RedactionTarget] = (), *,
                    artifact_id: UUID, blocks: Iterable[ExtractedTextBlock] = (),
                    region_sources: Iterable[SourceLocation] = (),
                    submission_id: UUID | None = None) -> SanitizedArtifact:
    """Publish a complete fresh PDF exclusively; never overwrite an existing file."""
    temporary = None
    published = False
    try:
        source_path, output_path = Path(source_path), Path(output_path)
        if source_path.resolve() == output_path.resolve() or output_path.exists() or source_path.stat().st_size > 25 * 1024 * 1024:
            raise ValueError("Invalid output destination or input size")
        data = redact_pdf(source_path.read_bytes(), targets, artifact_id=artifact_id,
            blocks=blocks, region_sources=region_sources, submission_id=submission_id)
        result = SanitizedArtifact(artifact_id=artifact_id, filename=output_path.name,
            mime_type="application/pdf", output_path=output_path.resolve(), size_bytes=len(data),
            sha256=sha256(data).hexdigest(), format_changed=False)
        with NamedTemporaryFile(dir=output_path.parent, prefix=".pii-redaction-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, output_path)  # Atomic exclusive publication on this filesystem.
        published = True
        return result
    except ProcessingError:
        raise
    except Exception:
        raise ProcessingError(ProcessingErrorCode.REDACTION_FAILED, "PDF redaction output could not be published.",
            submission_id=submission_id if isinstance(submission_id, UUID) else None,
            artifact_id=artifact_id if isinstance(artifact_id, UUID) else None) from None
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except Exception:
                if published:
                    try:
                        output_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                raise ProcessingError(ProcessingErrorCode.REDACTION_FAILED,
                    'PDF redaction output cleanup failed.',
                    submission_id=submission_id if isinstance(submission_id, UUID) else None,
                    artifact_id=artifact_id if isinstance(artifact_id, UUID) else None) from None
