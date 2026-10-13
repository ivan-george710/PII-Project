"""OCR embedded raster media as distinct, fingerprinted logical segments."""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from .models import ExtractedPage


def extract_media(extraction, ocr_engine):
    from app.engines.visual_detection.images import decode, MAX_BYTES
    prefix = 'word/media/' if extraction.file_type == 'docx' else 'ppt/media/'
    with ZipFile(extraction.source_path) as archive:
        for entry in archive.infolist():
            if not (entry.filename.startswith(prefix) or entry.filename.lower().startswith('docprops/thumbnail.')):
                continue
            if Path(entry.filename).suffix.lower() not in {'.png', '.jpg', '.jpeg'}:
                raise ValueError('Embedded image format is unsupported for OCR')
            if entry.file_size > MAX_BYTES:
                raise ValueError('Embedded image exceeds OCR size limit')
            payload = archive.read(entry)
            with decode(payload, 'display') as image, TemporaryDirectory() as directory:
                path = Path(directory) / 'image.png'
                image.save(path)
                blocks = ocr_engine.extract_image(path)
                source = dict(part=entry.filename, sha256=sha256(payload).hexdigest(),
                              width=image.width, height=image.height)
            number = max((p.page_number for p in extraction.pages), default=0) + 1
            extraction.pages.append(ExtractedPage(number, '\n'.join(b.text for b in blocks),
                                                  'media_ocr', blocks, source))
    extraction.structure.limitations.pop('media_without_ocr', None)
    return extraction
