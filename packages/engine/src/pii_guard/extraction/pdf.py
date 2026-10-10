from __future__ import annotations

from pathlib import Path
from uuid import UUID
from io import BytesIO

import pypdfium2 as pdfium

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.extraction.embedded_images import EmbeddedImage, ocr_embedded_images
from pii_guard.inspection.file_type import detect_file_type
from pii_guard.inspection.pdf_analysis import analyze_pdf
from pii_guard.models import ExtractedArtifact, ExtractedTextBlock, SourceLocation
from pii_guard.ocr.engine import OCRProvider


def extract_pdf(
    path: Path,
    *,
    artifact_id: UUID,
    filename: str,
    ocr_provider: OCRProvider,
    max_pages: int = 100,
    max_render_edge: int = 4096,
) -> ExtractedArtifact:
    detected = detect_file_type(path, artifact_id=artifact_id)
    if detected.file_format != "pdf":
        raise ProcessingError(
            ProcessingErrorCode.UNSUPPORTED_FILE,
            "Artifact is not a PDF.",
            artifact_id=artifact_id,
        )

    analysis = analyze_pdf(path, artifact_id=artifact_id, max_pages=max_pages)
    try:
        reader = PdfReader(str(path))
    except PdfReadError as exc:
        raise ProcessingError(
            ProcessingErrorCode.EXTRACTION_FAILED,
            "Malformed PDF could not be read.",
            artifact_id=artifact_id,
        ) from exc

    blocks: list[ExtractedTextBlock] = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            native_text = page.extract_text() or ""
        except Exception as exc:
            raise ProcessingError(
                ProcessingErrorCode.EXTRACTION_FAILED,
                f"Could not extract native text from PDF page {page_number}.",
                artifact_id=artifact_id,
            ) from exc

        if native_text:
            blocks.append(
                ExtractedTextBlock(
                    text=native_text,
                    extraction_method="native_text",
                    confidence=None,
                    location=SourceLocation(
                        artifact_id=artifact_id,
                        kind="native_text",
                        page_number=page_number,
                        slide_number=None,
                        source_ref=f"pdf:page:{page_number}:native_text",
                        start=0,
                        end=len(native_text),
                        bbox=None,
                    ),
                )
            )

        page_analysis = analysis.pages[page_number - 1]
        if page_analysis.requires_ocr:
            # Full-page rendering preserves clipping, repeated placements, rotation,
            # vector text and form content; raw image bytes cannot do that.
            images = [_render_page(path, page_number, artifact_id, max_render_edge)]
            blocks.extend(
                ocr_embedded_images(
                    images,
                    artifact_id=artifact_id,
                    ocr_provider=ocr_provider,
                )
            )

    return ExtractedArtifact(
        artifact_id=artifact_id,
        filename=filename,
        mime_type=detected.mime_type,
        file_type="pdf",
        blocks=blocks,
        warnings=[],
    )


def _render_page(path: Path, page_number: int, artifact_id: UUID, max_render_edge: int) -> EmbeddedImage:
    try:
        with pdfium.PdfDocument(str(path)) as document:
            page = document[page_number - 1]
            try:
                width, height = page.get_size()
                # Bound allocation without silently reducing OCR resolution.
                if width <= 0 or height <= 0:
                    raise ValueError("Invalid page dimensions")
                scale = 2.0
                if max(width, height) * scale > max_render_edge:
                    raise ProcessingError(ProcessingErrorCode.UNSUPPORTED_FILE, "PDF page exceeds the supported rendering dimensions.", artifact_id=artifact_id)
                bitmap = page.render(scale=scale)
                try:
                    with bitmap.to_pil() as image, BytesIO() as output:
                        image.save(output, format="PNG")
                        data = output.getvalue()
                finally:
                    bitmap.close()
            finally:
                page.close()
        return EmbeddedImage(data=data, extension=".png", source_ref=f"pdf:page:{page_number}:rendered", page_number=page_number, bbox=(0.0, 0.0, 1.0, 1.0))
    except ProcessingError:
        raise
    except Exception as exc:
        raise ProcessingError(ProcessingErrorCode.OCR_FAILED, f"Could not render PDF page {page_number} for OCR.", artifact_id=artifact_id) from exc
