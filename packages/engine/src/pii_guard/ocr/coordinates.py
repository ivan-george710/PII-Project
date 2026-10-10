from __future__ import annotations

from collections.abc import Sequence
from math import cos, sin, radians


def normalize_bbox(
    bbox: Sequence[float],
    *,
    width: int,
    height: int,
) -> tuple[float, float, float, float]:
    if width <= 0 or height <= 0:
        raise ValueError("image width and height must be positive")
    if len(bbox) != 4:
        raise ValueError("bbox must contain four values")

    x, y, box_width, box_height = (float(value) for value in bbox)
    return _clamp_normalized(
        x / width,
        y / height,
        box_width / width,
        box_height / height,
    )


def normalize_quad(
    quad: Sequence[Sequence[float]],
    *,
    width: int,
    height: int,
) -> tuple[float, float, float, float]:
    if width <= 0 or height <= 0:
        raise ValueError("image width and height must be positive")
    if len(quad) != 4:
        raise ValueError("quad must contain four points")

    xs = [float(point[0]) for point in quad]
    ys = [float(point[1]) for point in quad]
    x = min(xs)
    y = min(ys)
    box_width = max(xs) - x
    box_height = max(ys) - y

    return normalize_bbox((x, y, box_width, box_height), width=width, height=height)


def map_child_bbox_to_parent(
    child_bbox: tuple[float, float, float, float],
    parent_bbox: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    parent_x, parent_y, parent_width, parent_height = parent_bbox
    child_x, child_y, child_width, child_height = child_bbox
    return _clamp_normalized(
        parent_x + child_x * parent_width,
        parent_y + child_y * parent_height,
        child_width * parent_width,
        child_height * parent_height,
    )


def map_picture_bbox_to_slide(
    box: tuple[float, float, float, float],
    parent: tuple[float, float, float, float],
    *, crop: tuple[float, float, float, float], rotation: float,
    slide_size: tuple[int, int],
) -> tuple[float, float, float, float] | None:
    # Crop in image coordinates, rotate in physical slide units, then normalize.
    left, top, right, bottom = crop
    x, y, width, height = box
    x1, y1 = max(x, left), max(y, top)
    x2, y2 = min(x + width, 1 - right), min(y + height, 1 - bottom)
    if x2 <= x1 or y2 <= y1:
        return None
    px, py, pw, ph = parent
    sw, sh = slide_size
    angle = radians(rotation)
    points = []
    for bx, by in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
        dx = ((bx - left) / (1 - left - right) - 0.5) * pw * sw
        dy = ((by - top) / (1 - top - bottom) - 0.5) * ph * sh
        points.append(((px + pw / 2) + (dx * cos(angle) - dy * sin(angle)) / sw,
                       (py + ph / 2) + (dx * sin(angle) + dy * cos(angle)) / sh))
    xmin = max(0.0, min(p[0] for p in points))
    ymin = max(0.0, min(p[1] for p in points))
    xmax = min(1.0, max(p[0] for p in points))
    ymax = min(1.0, max(p[1] for p in points))
    if xmax <= xmin or ymax <= ymin:
        return None
    return (xmin, ymin, xmax - xmin, ymax - ymin)


def _clamp_normalized(
    x: float,
    y: float,
    width: float,
    height: float,
) -> tuple[float, float, float, float]:
    x = max(0.0, min(1.0, x))
    y = max(0.0, min(1.0, y))
    width = max(0.0, min(1.0 - x, width))
    height = max(0.0, min(1.0 - y, height))
    return (x, y, width, height)
