from __future__ import annotations

from pii_guard.ocr import map_child_bbox_to_parent, normalize_bbox, normalize_quad
import os
from pathlib import Path
import pytest


def test_normalize_pixel_bbox() -> None:
    assert normalize_bbox((10, 20, 30, 40), width=100, height=200) == (
        0.1,
        0.1,
        0.3,
        0.2,
    )


def test_normalize_quad_to_top_left_bbox() -> None:
    assert normalize_quad(
        ((10, 20), (40, 20), (40, 60), (10, 60)),
        width=100,
        height=200,
    ) == (0.1, 0.1, 0.3, 0.2)


def test_map_child_bbox_to_parent() -> None:
    assert map_child_bbox_to_parent(
        (0.25, 0.25, 0.5, 0.5),
        (0.1, 0.2, 0.4, 0.6),
    ) == (0.2, 0.35, 0.2, 0.3)


@pytest.mark.integration
@pytest.mark.skipif(os.environ.get("PII_GUARD_REAL_OCR") != "1", reason="Set PII_GUARD_REAL_OCR=1 to run real OCR")
def test_real_ocr_synthetic_scan() -> None:
    pytest.importorskip("rapidocr_onnxruntime")
    from pii_guard.ocr import RapidOCREngine
    blocks = RapidOCREngine().recognize_image(Path(__file__).parent / "fixtures" / "scan.png")
    assert "HELLO" == "".join(block.text.strip() for block in blocks)
    assert blocks
    for block in blocks:
        x, y, width, height = block.bbox
        assert 0 <= x < x + width <= 1
        assert 0 <= y < y + height <= 1
        assert 0 <= block.confidence <= 1


@pytest.mark.parametrize("bbox,confidence", [((0,0,0,1),0.9), ((0.8,0,0.3,0.1),0.9), ((0,0,0.1,0.1),float("nan"))])
def test_invalid_ocr_regions_rejected(bbox: tuple, confidence: float) -> None:
    from pii_guard.ocr import OCRBlock
    with pytest.raises(ValueError):
        OCRBlock("text", confidence, bbox)


def test_picture_rotation_uses_physical_nonsquare_slide_units() -> None:
    from pii_guard.ocr.coordinates import map_picture_bbox_to_slide
    assert map_picture_bbox_to_slide((0, 0, 0.5, 0.5), (0.2, 0.2, 0.4, 0.4),
        crop=(0, 0, 0, 0), rotation=90, slide_size=(200, 100)) == pytest.approx((0.4, 0, 0.1, 0.4))


def test_picture_crop_excludes_fully_invisible_regions() -> None:
    from pii_guard.ocr.coordinates import map_picture_bbox_to_slide
    assert map_picture_bbox_to_slide((0, 0, 0.1, 0.1), (0, 0, 1, 1),
        crop=(0.2, 0, 0, 0), rotation=0, slide_size=(200, 100)) is None
