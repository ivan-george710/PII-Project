from __future__ import annotations

from pathlib import Path
from uuid import UUID

from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.inspection.file_type import detect_file_type
from pii_guard.models import ExtractedArtifact, ExtractedTextBlock, SourceLocation
from pii_guard.ocr.engine import OCRProvider, inspect_image_dimensions, recognize_image


def extract_image(
    path: Path,
    *,
    artifact_id: UUID,
    filename: str,
    ocr_provider: OCRProvider,
) -> ExtractedArtifact:
    detected = detect_file_type(path, artifact_id=artifact_id)
    if detected.file_format not in {"png", "jpeg"}:
        raise ProcessingError(
            ProcessingErrorCode.UNSUPPORTED_FILE,
            "Artifact is not a supported image.",
            artifact_id=artifact_id,
        )

    inspect_image_dimensions(path, artifact_id=artifact_id)
    ocr_blocks = recognize_image(
        ocr_provider,
        path,
        artifact_id=artifact_id,
        source_ref="image",
    )

    blocks: list[ExtractedTextBlock] = []
    for index, block in enumerate(ocr_blocks):
        if not block.text:
            continue
        blocks.append(
            ExtractedTextBlock(
                text=block.text,
                extraction_method="ocr",
                confidence=block.confidence,
                location=SourceLocation(
                    artifact_id=artifact_id,
                    kind="ocr",
                    page_number=None,
                    slide_number=None,
                    source_ref=f"image:ocr:{index}",
                    start=0,
                    end=len(block.text),
                    bbox=block.bbox,
                ),
            )
        )

    return ExtractedArtifact(
        artifact_id=artifact_id,
        filename=filename,
        mime_type=detected.mime_type,
        file_type=detected.file_format,
        blocks=blocks,
        warnings=[],
    )
