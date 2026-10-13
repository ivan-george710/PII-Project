from pathlib import Path
from tempfile import TemporaryDirectory
from collections import OrderedDict
from hashlib import sha256
from copy import deepcopy

from rapidocr_onnxruntime import RapidOCR

from .models import ExtractedPage, ExtractionResult, OCRTextBlock, PDFSourceMap
from .office import source_hash


class OCREngine:
    """OCR engine backed by RapidOCR ONNX Runtime."""

    def __init__(self):
        self.engine = RapidOCR()
        self._cache = OrderedDict()

    def extract_image(self, image_path: Path) -> list[OCRTextBlock]:
        key=sha256(image_path.read_bytes()).hexdigest()
        if key in self._cache:
            self._cache.move_to_end(key)
            return deepcopy(self._cache[key])
        results, _ = self.engine(str(image_path))

        if not results:
            self._cache[key]=[]
            if len(self._cache)>64:self._cache.popitem(last=False)
            return []

        blocks = []

        for item in results:
            bounding_box, text, confidence = item

            blocks.append(
                OCRTextBlock(
                    text=str(text),
                    confidence=float(confidence),
                    bounding_box=bounding_box,
                )
            )

        self._cache[key]=deepcopy(blocks)
        if len(self._cache)>64:self._cache.popitem(last=False)
        return blocks

    def extract_pdf(self, pdf_path: Path, dpi: int = 200) -> ExtractionResult:
        import pymupdf as fitz
        with fitz.open(pdf_path) as document:
            pages = [self.extract_pdf_page(pdf_path, number, dpi)
                     for number in range(1, len(document) + 1)]
        return ExtractionResult(pdf_path, pdf_path.name, "pdf", pages,
            pdf_source=PDFSourceMap(source_hash(pdf_path), {str(p.page_number): dpi for p in pages}))

    def extract_pdf_page(self, pdf_path: Path, page_number: int, dpi: int = 200) -> ExtractedPage:
        """OCR original embedded pixels and map boxes to the canonical output raster.

        Retain exact native text as blocks; OCR adds text from images without
        duplicating native lines. A selectable page number never suppresses OCR.
        """
        import pymupdf as fitz
        with fitz.open(pdf_path) as document:
            page = document[page_number - 1]
            if page.cropbox != page.mediabox:
                raise ValueError("Cropped PDF geometry is not supported for OCR redaction")
            pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False, annots=False)
            blocks = []
            placements = page.get_image_info(xrefs=True)
            with TemporaryDirectory() as directory:
                image_path = Path(directory) / "source.png"
                if placements and all(item.get('xref') for item in placements):
                    from app.engines.visual_detection.images import decode
                    cache = {}
                    for item in placements:
                        xref = item['xref']
                        if xref not in cache:
                            payload = document.extract_image(xref)['image']
                            with decode(payload, 'raw') as image:
                                image.save(image_path)
                                cache[xref] = (image.width,image.height,self.extract_image(image_path))
                        width,height,source_blocks = cache[xref]
                        transform = fitz.Matrix(item['transform'])
                        for block in source_blocks:
                            points = []
                            for x,y in block.bounding_box:
                                point = fitz.Point(x/width,y/height) * transform * page.rotation_matrix
                                points.append([min(pix.width,max(0,point.x*dpi/72)),
                                               min(pix.height,max(0,point.y*dpi/72))])
                            if max(p[0] for p in points)<=min(p[0] for p in points) or max(p[1] for p in points)<=min(p[1] for p in points):
                                continue
                            blocks.append(OCRTextBlock(block.text,block.confidence,points))
                else:
                    pix.save(image_path)
                    blocks = self.extract_image(image_path)
            # Rotated native glyph coordinates need their page rotation transform.
            scale = dpi / 72
            native = []
            native_rects = []
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    text = "".join(span["text"] for span in line.get("spans", []))
                    if not text.strip():
                        continue
                    rect = fitz.Rect(line["bbox"]) * page.rotation_matrix
                    rect = fitz.Rect([v * scale for v in rect])
                    native_rects.append(rect)
                    native.append(OCRTextBlock(text, 1.0,
                        [[rect.x0, rect.y0], [rect.x1, rect.y0],
                         [rect.x1, rect.y1], [rect.x0, rect.y1]]))
            retained = []
            for block in blocks:
                points = block.bounding_box
                rect = fitz.Rect(min(p[0] for p in points), min(p[1] for p in points),
                                 max(p[0] for p in points), max(p[1] for p in points))
                if any((rect & other).get_area() / max(rect.get_area(), 1) > .5
                       for other in native_rects):
                    continue
                retained.append(block)
            blocks = sorted(native + retained,
                            key=lambda b: (min(p[1] for p in b.bounding_box), min(p[0] for p in b.bounding_box)))
        return ExtractedPage(page_number, "\n".join(b.text for b in blocks), "ocr", blocks)

    def extract_line(self, image_path):
        """Recognize a known text-line crop without rerunning box detection."""
        results,_=self.engine(str(image_path),use_det=False,use_cls=False,use_rec=True)
        return ' '.join(str(row[0]) for row in results or [] if len(row)>=2 and float(row[1])>=.5)
