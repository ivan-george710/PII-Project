from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID
from math import isfinite

from PIL import Image, UnidentifiedImageError

from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.ocr.coordinates import normalize_bbox, normalize_quad


@dataclass(frozen=True)
class OCRBlock:
    text: str
    confidence: float
    bbox: tuple[float, float, float, float]

    def __post_init__(self) -> None:
        x, y, width, height = self.bbox
        if not all(isfinite(v) and 0 <= v <= 1 for v in (*self.bbox, self.confidence)) or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
            raise ValueError("Invalid OCR geometry or confidence")


class OCRProvider(Protocol):
    def recognize_image(
        self,
        image_path: Path,
        *,
        artifact_id: UUID | None = None,
        source_ref: str | None = None,
    ) -> list[OCRBlock]:
        ...


class RapidOCREngine:
    def __init__(self) -> None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:
            raise ProcessingError(
                ProcessingErrorCode.OCR_FAILED,
                "RapidOCR is not installed. Install the engine OCR extra.",
            ) from exc

        try:
            self._engine = RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1)
        except Exception as exc:
            raise ProcessingError(ProcessingErrorCode.OCR_FAILED, "OCR models could not be initialized.") from exc

    def recognize_image(
        self,
        image_path: Path,
        *,
        artifact_id: UUID | None = None,
        source_ref: str | None = None,
    ) -> list[OCRBlock]:
        try:
            with Image.open(image_path) as image:
                width, height = image.size
        except (OSError, UnidentifiedImageError) as exc:
            raise ProcessingError(
                ProcessingErrorCode.OCR_FAILED,
                "Image could not be opened for OCR.",
                artifact_id=artifact_id,
            ) from exc

        try:
            results, _ = self._engine(str(image_path))
        except Exception as exc:
            raise ProcessingError(
                ProcessingErrorCode.OCR_FAILED,
                "OCR failed for image content.",
                artifact_id=artifact_id,
            ) from exc

        try:
            blocks: list[OCRBlock] = []
            for result in results or []:
                raw_box, text, confidence = result
                bbox = normalize_quad(raw_box, width=width, height=height)
                if text:
                    blocks.append(OCRBlock(str(text), float(confidence), bbox))
            return blocks
        except Exception as exc:
            raise ProcessingError(ProcessingErrorCode.OCR_FAILED, "OCR returned invalid regions.", artifact_id=artifact_id) from exc


def recognize_image(provider: OCRProvider, path: Path, *, artifact_id: UUID,
                    source_ref: str) -> list[OCRBlock]:
    """Keep provider failures and malformed results inside the error contract."""
    try:
        inspect_image_dimensions(path, artifact_id=artifact_id)
        return [OCRBlock(block.text, block.confidence, block.bbox)
                for block in provider.recognize_image(path, artifact_id=artifact_id, source_ref=source_ref)]
    except ProcessingError as exc:
        raise ProcessingError(ProcessingErrorCode.OCR_FAILED, "Image content could not be recognized.", artifact_id=artifact_id) from exc
    except Exception as exc:
        raise ProcessingError(ProcessingErrorCode.OCR_FAILED, "Image content could not be recognized.", artifact_id=artifact_id) from exc


def inspect_image_dimensions(
    image_path: Path,
    *,
    artifact_id: UUID | None = None,
) -> tuple[int, int]:
    try:
        with Image.open(image_path) as image:
            if getattr(image, "n_frames", 1) != 1:
                raise ProcessingError(ProcessingErrorCode.UNSUPPORTED_FILE, "Multi-frame images are not supported.", artifact_id=artifact_id)
            image.verify()
        with Image.open(image_path) as image:
            return image.size
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ProcessingError(
            ProcessingErrorCode.EXTRACTION_FAILED,
            "Image content could not be opened.",
            artifact_id=artifact_id,
        ) from exc


def block_from_pixel_bbox(
    text: str,
    confidence: float,
    bbox: tuple[float, float, float, float],
    *,
    width: int,
    height: int,
) -> OCRBlock:
    return OCRBlock(
        text=text,
        confidence=confidence,
        bbox=normalize_bbox(bbox, width=width, height=height),
    )
