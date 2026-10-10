from __future__ import annotations

from collections.abc import Iterable
from io import BytesIO
from math import ceil, floor
from typing import Literal
from uuid import UUID

from PIL import Image, ImageOps
from pydantic import Field, StrictBool, StrictInt

from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.models import EngineBaseModel, SourceLocation
from pii_guard.rules.policy import RedactionTarget
from pii_guard.redaction.metadata import verify_encoded_image_metadata


MAX_IMAGE_PIXELS = 16_777_216


class ImageRedactionResult(EngineBaseModel):
    data: bytes = Field(exclude=True, repr=False)
    mime_type: Literal["image/png", "image/jpeg"]
    width: StrictInt
    height: StrictInt
    format_changed: StrictBool
    warnings: tuple[str, ...] = ()


def _source_key(location: SourceLocation) -> tuple:
    return (location.artifact_id, location.kind, location.page_number,
            location.slide_number, location.source_ref)


def _validate_regions(targets: Iterable[RedactionTarget], sources: Iterable[SourceLocation],
                      artifact_id: UUID) -> list[SourceLocation]:
    known = {}
    for source in sources:
        if not isinstance(source, SourceLocation):
            raise ValueError("Invalid source contract")
        source = SourceLocation.model_validate(source.model_dump(warnings=False))
        if source.artifact_id != artifact_id or source.kind not in {"ocr", "face"} or source.bbox is None:
            raise ValueError("Invalid region source")
        if source.kind == "ocr" and source.start != 0:
            raise ValueError("Expected an original OCR block")
        key = _source_key(source)
        if key in known and known[key] != source:
            raise ValueError("Conflicting source units")
        known[key] = source
    locations = []
    for target in targets:
        if not isinstance(target, RedactionTarget):
            raise ValueError("Only enabled policy targets are accepted")
        location = RedactionTarget.model_validate(target.model_dump(warnings=False)).location
        source = known.get(_source_key(location))
        if source is None or source.bbox != location.bbox:
            raise ValueError("Region source mismatch")
        if location.kind == "ocr" and not 0 <= location.start < location.end <= source.end:
            raise ValueError("OCR span is outside original block")
        if location.kind == "face" and (location.start is not None or location.end is not None):
            raise ValueError("Faces require regions, not text offsets")
        locations.append(location)
    return locations


def _pixel_box(box: tuple[float, float, float, float], width: int, height: int) -> tuple[int, int, int, int]:
    x, y, w, h = box
    return (max(0, floor(x * width)), max(0, floor(y * height)),
            min(width, ceil((x + w) * width)), min(height, ceil((y + h) * height)))


def _paint_image(image: Image.Image, boxes: Iterable[tuple[int, int, int, int]]) -> Image.Image:
    # Rebuild the raster to remove metadata, thumbnails and palette payloads.
    mode = "RGBA" if "A" in image.getbands() or "transparency" in image.info else "RGB"
    converted = image.convert(mode)
    fresh = Image.frombytes(mode, converted.size, converted.tobytes())
    converted.close()
    if mode == 'RGBA':
        # Fully transparent RGB is an invisible alternate representation. Clear
        # it without changing any displayed pixels or the alpha channel.
        with fresh.getchannel('A') as alpha:
            with alpha.point(lambda value: 255 if value == 0 else 0) as hidden:
                fresh.paste((0, 0, 0, 0), mask=hidden)
    for box in sorted(set(boxes)):
        fresh.paste((0, 0, 0, 255) if mode == "RGBA" else (0, 0, 0), box)
    return fresh


def _encode_image(image: Image.Image, output_format: str) -> bytes:
    with BytesIO() as output:
        if output_format == "JPEG":
            # Flatten alpha against white; no invisible RGB values survive.
            rgb = Image.new("RGB", image.size, "white")
            rgb.paste(image, mask=image.getchannel("A") if image.mode == "RGBA" else None)
            try:
                rgb.save(output, format="JPEG", quality=95, subsampling=0)
            finally:
                rgb.close()
        else:
            image.save(output, format="PNG")
        data = output.getvalue()
        verify_encoded_image_metadata(data, output_format)
        return data


def redact_image(data: bytes, targets: Iterable[RedactionTarget] = (), *, artifact_id: UUID,
                 sources: Iterable[SourceLocation] = (), image_ref: str = "image",
                 coordinate_frame: Literal["raw", "display"] = "raw",
                 output_format: Literal["PNG", "JPEG"] | None = None,
                 submission_id: UUID | None = None) -> ImageRedactionResult:
    """Replace pixels in image-local normalized regions and encode a fresh image.

    Raw frame matches extraction's stored raster dimensions. Display frame means
    EXIF-transposed pixels. Parent page/slide coordinates require an explicit inverse
    mapping at their document renderer; they are not accepted here.
    """
    try:
        if not isinstance(data, bytes) or len(data) > 25 * 1024 * 1024 or not isinstance(artifact_id, UUID):
            raise ValueError("Invalid image input")
        if coordinate_frame not in {"raw", "display"} or output_format not in {None, "PNG", "JPEG"}:
            raise ValueError("Unsupported image rendering options")
        locations = _validate_regions(targets, sources, artifact_id)
        for location in locations:
            ref = location.source_ref or ""
            valid_ref = ref == image_ref if location.kind == "face" else (
                ref.startswith(f"{image_ref}:ocr:") and ref[len(image_ref) + 5:].isascii()
                and ref[len(image_ref) + 5:].isdigit())
            if not valid_ref or location.page_number is not None or location.slide_number is not None:
                raise ValueError("Region does not belong to this image-local frame")
        with Image.open(BytesIO(data)) as original:
            if original.format not in {"PNG", "JPEG"} or getattr(original, "n_frames", 1) != 1:
                raise ValueError("Unsupported image encoding")
            if original.width * original.height > MAX_IMAGE_PIXELS:
                raise ValueError("Image exceeds pixel limit")
            original.load()
            had_metadata = bool(original.getexif()) or bool(set(original.info) -
                {'jfif', 'jfif_version', 'jfif_unit', 'jfif_density', 'transparency'})
            input_format = original.format
            chosen = output_format or input_format
            oriented = ImageOps.exif_transpose(original) if coordinate_frame == "display" else original.copy()
            try:
                boxes = [_pixel_box(location.bbox, *oriented.size) for location in locations]
                with _paint_image(oriented, boxes) as painted:
                    # Raw-frame targets are painted before the same orientation
                    # transform as the rest of the raster. Orientation is baked in.
                    if coordinate_frame == "raw":
                        painted.info["exif"] = original.getexif().tobytes()
                    with ImageOps.exif_transpose(painted) as displayed:
                        displayed.info.clear()
                        encoded = _encode_image(displayed, chosen)
                        width, height = displayed.size
            finally:
                oriented.close()
        changed = chosen != input_format
        return ImageRedactionResult(data=encoded, mime_type="image/png" if chosen == "PNG" else "image/jpeg",
            width=width, height=height, format_changed=changed,
            warnings=(("Image metadata was removed.",) if had_metadata else ()) +
                (("Image encoding changed for sanitized output.",) if changed else ()))
    except Exception:
        raise ProcessingError(ProcessingErrorCode.REDACTION_FAILED,
            "Image redaction failed: unsupported content or invalid source regions.",
            submission_id=submission_id if isinstance(submission_id, UUID) else None,
            artifact_id=artifact_id if isinstance(artifact_id, UUID) else None) from None
