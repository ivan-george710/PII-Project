from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID
from xml.etree import ElementTree as ET

from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.models import ExtractedTextBlock, SourceLocation
from pii_guard.ocr.coordinates import map_child_bbox_to_parent, map_picture_bbox_to_slide
from pii_guard.ocr.engine import OCRProvider, recognize_image


@dataclass(frozen=True)
class EmbeddedImage:
    data: bytes
    extension: str
    source_ref: str
    bbox: tuple[float, float, float, float] | None = None
    page_number: int | None = None
    slide_number: int | None = None
    rotation: float = 0.0
    crop: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    slide_size: tuple[int, int] | None = None


def part_paragraphs(part: object, namespace: str) -> list[str]:
    """Include paragraphs in tables, groups, text boxes and ancillary parts."""
    root = ET.fromstring(part.blob)
    texts = []
    for paragraph in root.iter(f"{{{namespace}}}p"):
        pieces = []
        def paragraph_nodes(node: ET.Element):
            yield node
            for child in node:
                if child.tag != f"{{{namespace}}}p":
                    yield from paragraph_nodes(child)

        for node in paragraph_nodes(paragraph):
            if node.tag == f"{{{namespace}}}t":
                pieces.append(node.text or "")
            elif node.tag in {f"{{{namespace}}}tab"}:
                pieces.append("\t")
            elif node.tag in {f"{{{namespace}}}br", f"{{{namespace}}}cr"}:
                pieces.append("\n")
        if pieces:
            texts.append("".join(pieces))
    # Chart caches and presentation comments use distinct text-bearing elements.
    extra_tags = {"{http://schemas.openxmlformats.org/drawingml/2006/chart}v",
                  "{http://schemas.openxmlformats.org/presentationml/2006/main}text"}
    texts.extend(node.text for node in root.iter() if node.tag in extra_tags and node.text)
    return texts


def part_images(part: object, *, prefix: str) -> list[EmbeddedImage]:
    images = []
    for rel_id, rel in part.rels.items():
        if rel.reltype.endswith(("/oleObject", "/package", "/aFChunk")):
            raise ProcessingError(ProcessingErrorCode.UNSUPPORTED_FILE, "Unsupported embedded document content.")
        if not rel.reltype.endswith("/image"):
            continue
        if rel.is_external:
            raise ProcessingError(ProcessingErrorCode.UNSUPPORTED_FILE, "External image content is not supported.")
        target = rel.target_part
        images.append(EmbeddedImage(data=target.blob, extension=Path(str(target.partname)).suffix, source_ref=f"{prefix}:part:{part.partname}:image:{rel_id}"))
    return images


def ocr_embedded_images(
    images: list[EmbeddedImage],
    *,
    artifact_id: UUID,
    ocr_provider: OCRProvider,
) -> list[ExtractedTextBlock]:
    blocks: list[ExtractedTextBlock] = []
    for image in images:
        blocks.extend(
            ocr_embedded_image(
                image,
                artifact_id=artifact_id,
                ocr_provider=ocr_provider,
            )
        )
    return blocks


def ocr_embedded_image(
    image: EmbeddedImage,
    *,
    artifact_id: UUID,
    ocr_provider: OCRProvider,
) -> list[ExtractedTextBlock]:
    suffix = image.extension if image.extension.startswith(".") else f".{image.extension}"
    try:
        with TemporaryDirectory(prefix="pii-guard-ocr-") as directory:
            temp_path = Path(directory) / f"image{suffix}"
            temp_path.write_bytes(image.data)
            ocr_blocks = recognize_image(
                ocr_provider,
                temp_path,
                artifact_id=artifact_id,
                source_ref=image.source_ref,
            )
    except ProcessingError:
        raise
    except Exception as exc:
        raise ProcessingError(
            ProcessingErrorCode.OCR_FAILED,
            "OCR failed for embedded image content.",
            artifact_id=artifact_id,
        ) from exc

    extracted: list[ExtractedTextBlock] = []
    for index, block in enumerate(ocr_blocks):
        if not block.text:
            continue
        bbox = block.bbox
        if image.bbox is not None:
            if image.slide_size is not None:
                bbox = map_picture_bbox_to_slide(block.bbox, image.bbox, crop=image.crop,
                                                rotation=image.rotation, slide_size=image.slide_size)
                if bbox is None:
                    continue
            else:
                bbox = map_child_bbox_to_parent(block.bbox, image.bbox)
        extracted.append(
            ExtractedTextBlock(
                text=block.text,
                extraction_method="ocr",
                confidence=block.confidence,
                location=SourceLocation(
                    artifact_id=artifact_id,
                    kind="ocr",
                    page_number=image.page_number,
                    slide_number=image.slide_number,
                    source_ref=f"{image.source_ref}:ocr:{index}",
                    start=0,
                    end=len(block.text),
                    bbox=bbox,
                ),
            )
        )
    return extracted

