from __future__ import annotations

from pathlib import Path
from uuid import UUID

from docx import Document

from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.extraction.embedded_images import ocr_embedded_images, part_paragraphs, part_images
from pii_guard.inspection.file_type import detect_file_type
from pii_guard.models import ExtractedArtifact, ExtractedTextBlock, SourceLocation
from pii_guard.ocr.engine import OCRProvider


def extract_docx(
    path: Path,
    *,
    artifact_id: UUID,
    filename: str,
    ocr_provider: OCRProvider,
) -> ExtractedArtifact:
    detected = detect_file_type(path, artifact_id=artifact_id)
    if detected.file_format != "docx":
        raise ProcessingError(
            ProcessingErrorCode.UNSUPPORTED_FILE,
            "Artifact is not a DOCX document.",
            artifact_id=artifact_id,
        )

    try:
        document = Document(str(path))
    except Exception as exc:
        raise ProcessingError(
            ProcessingErrorCode.EXTRACTION_FAILED,
            "DOCX document could not be opened.",
            artifact_id=artifact_id,
        ) from exc

    blocks: list[ExtractedTextBlock] = []
    try:
        images = []
        for part in document.part.package.parts:
            name = str(part.partname)
            if name.startswith("/word/") and name.endswith(".xml"):
                for index, text in enumerate(part_paragraphs(part, "http://schemas.openxmlformats.org/wordprocessingml/2006/main")):
                    blocks.append(_native_block(artifact_id, text, f"docx:part:{name}:paragraph:{index}"))
            images.extend(part_images(part, prefix="docx"))
        blocks.extend(ocr_embedded_images(images, artifact_id=artifact_id, ocr_provider=ocr_provider))
    except ProcessingError as exc:
        exc.artifact_id = artifact_id
        raise
    except Exception as exc:
        raise ProcessingError(ProcessingErrorCode.EXTRACTION_FAILED, "DOCX content could not be extracted.", artifact_id=artifact_id) from exc

    return ExtractedArtifact(
        artifact_id=artifact_id,
        filename=filename,
        mime_type=detected.mime_type,
        file_type="docx",
        blocks=blocks,
        warnings=[],
    )


def _native_block(artifact_id: UUID, text: str, source_ref: str) -> ExtractedTextBlock:
    return ExtractedTextBlock(
        text=text,
        extraction_method="native_text",
        confidence=None,
        location=SourceLocation(
            artifact_id=artifact_id,
            kind="native_text",
            page_number=None,
            slide_number=None,
            source_ref=source_ref,
            start=0,
            end=len(text),
            bbox=None,
        ),
    )
