from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

from pypdf import PdfReader

from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.inspection.file_type import detect_file_type


MAX_PDF_PAGES = 100
PDFExtractionStrategy = Literal["text", "ocr", "hybrid", "empty"]


@dataclass(frozen=True)
class PDFPageAnalysis:
    page_number: int
    has_native_text: bool
    has_images: bool
    requires_ocr: bool
    is_blank: bool


@dataclass(frozen=True)
class PDFAnalysis:
    total_pages: int
    text_pages: int
    image_only_pages: int
    mixed_pages: int
    blank_pages: int
    requires_ocr: bool
    extraction_strategy: PDFExtractionStrategy
    pages: tuple[PDFPageAnalysis, ...]


def analyze_pdf(
    path: Path,
    *,
    artifact_id: UUID | None = None,
    max_pages: int = MAX_PDF_PAGES,
) -> PDFAnalysis:
    if detect_file_type(path, artifact_id=artifact_id).file_format != "pdf":
        raise ProcessingError(ProcessingErrorCode.UNSUPPORTED_FILE, "Artifact is not a PDF.", artifact_id=artifact_id)
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise ProcessingError(ProcessingErrorCode.ENCRYPTED_FILE, "Encrypted PDFs are not supported.", artifact_id=artifact_id)
        total_pages = len(reader.pages)
    except ProcessingError:
        raise
    except Exception as exc:
        raise ProcessingError(
            ProcessingErrorCode.EXTRACTION_FAILED,
            "Malformed PDF could not be read.",
            artifact_id=artifact_id,
        ) from exc

    if total_pages > max_pages:
        raise ProcessingError(
            ProcessingErrorCode.UNSUPPORTED_FILE,
            "PDF exceeds the supported page limit.",
            artifact_id=artifact_id,
        )

    pages: list[PDFPageAnalysis] = []
    text_pages = 0
    image_only_pages = 0
    mixed_pages = 0
    blank_pages = 0

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
            has_native_text = bool(text.strip())
            has_images = _page_has_images(page)
            content = page.get_contents()
            operations = content.operations if content is not None else []
            # Render vector outlines, forms, inline images and unextractable glyphs too.
            visual_content = any(op in {b"Do", b"INLINE IMAGE", b"sh", b"S", b"s", b"f", b"F", b"f*", b"B", b"B*", b"b", b"b*"} for _, op in operations)
            unextractable_text = not has_native_text and any(op in {b"Tj", b"TJ", b"'", b'"'} for _, op in operations)
            requires_ocr = has_images or visual_content or unextractable_text or bool(page.get("/Annots"))
        except Exception as exc:
            raise ProcessingError(
                ProcessingErrorCode.EXTRACTION_FAILED,
                f"Could not inspect PDF page {page_number}.",
                artifact_id=artifact_id,
            ) from exc

        is_blank = not has_native_text and not requires_ocr

        if has_native_text and requires_ocr:
            mixed_pages += 1
        elif has_native_text:
            text_pages += 1
        elif requires_ocr:
            image_only_pages += 1
        else:
            blank_pages += 1

        pages.append(
            PDFPageAnalysis(
                page_number=page_number,
                has_native_text=has_native_text,
                has_images=has_images,
                requires_ocr=requires_ocr,
                is_blank=is_blank,
            )
        )

    ocr_pages = image_only_pages + mixed_pages
    if not pages:
        extraction_strategy: PDFExtractionStrategy = "empty"
    elif ocr_pages and (text_pages or mixed_pages or blank_pages):
        extraction_strategy = "hybrid"
    elif ocr_pages:
        extraction_strategy = "ocr"
    else:
        extraction_strategy = "text"

    return PDFAnalysis(
        total_pages=total_pages,
        text_pages=text_pages,
        image_only_pages=image_only_pages,
        mixed_pages=mixed_pages,
        blank_pages=blank_pages,
        requires_ocr=ocr_pages > 0,
        extraction_strategy=extraction_strategy,
        pages=tuple(pages),
    )


def _page_has_images(page: object) -> bool:
    # Resources identify images without decoding them. Decoding failures must not
    # turn a scanned page into an apparently blank page.
    resources = page.get("/Resources", {})
    resources = resources.get_object() if hasattr(resources, "get_object") else resources
    objects = resources.get("/XObject", {})
    objects = objects.get_object() if hasattr(objects, "get_object") else objects
    return any(obj.get_object().get("/Subtype") == "/Image" for obj in objects.values())
