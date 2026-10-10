"""Spark's tiled detection, deduplication and protected bounds, using CPU YuNet.

Coordinates are normalized in the raw raster frame used by extraction/rendering.
All faces are considered; Spark's optional subject classifier is not a company rule.
"""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from threading import Lock
from uuid import UUID

from PIL import Image

from pii_guard.detection.validation import DetectionCandidate
from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.models import SourceLocation

MODEL_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"


def same_face(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    overlap = max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(
        0, min(ay + ah, by + bh) - max(ay, by)
    )
    small, large = sorted((aw * ah, bw * bh))
    return overlap / max(aw * ah + bw * bh - overlap, 1e-9) > 0.35 or (
        overlap / max(small, 1e-9) > 0.8 and large / max(small, 1e-9) < 2.5
    )


class FaceDetector:
    def __init__(self, model_path: Path | None = None):
        try:
            import cv2

            self.cv2 = cv2
            path = (
                model_path
                or Path(__file__).parents[1]
                / "model_assets/face_detection_yunet_2023mar.onnx"
            )
            if sha256(path.read_bytes()).hexdigest() != MODEL_SHA256:
                raise ValueError("Untrusted face model")
            self.model = cv2.FaceDetectorYN.create(
                str(path), "", (320, 320), 0.35, 0.3, 5000
            )
            self.lock = Lock()
        except Exception:
            raise ProcessingError(
                ProcessingErrorCode.FACE_DETECTION_FAILED,
                "Required face model is unavailable.",
            ) from None

    def detect(
        self,
        data: bytes,
        *,
        artifact_id: UUID,
        source_ref: str,
        page_number: int | None = None,
        slide_number: int | None = None,
        placement=None,
    ) -> list[DetectionCandidate]:
        try:
            import numpy as np

            with Image.open(BytesIO(data)) as image:
                if (
                    image.width * image.height > 16_777_216
                    or getattr(image, "n_frames", 1) != 1
                ):
                    raise ValueError("Unsupported image")
                rgb = np.array(image.convert("RGB"))
            height, width = rgb.shape[:2]
            candidates = []
            # Orientation passes cover photos with EXIF rotation while returning
            # raw-raster boxes; the encoder subsequently bakes in EXIF orientation.
            for rotation in range(4):
                rotated = np.ascontiguousarray(np.rot90(rgb, rotation))
                rh, rw = rotated.shape[:2]
                tiles = [(0, 0, rw, rh)]
                if rotation == 0 and max(rw, rh) >= 600:
                    tiles += [
                        (
                            int(x * rw),
                            int(y * rh),
                            min(rw, int((x + 0.45) * rw)),
                            min(rh, int((y + 0.45) * rh)),
                        )
                        for y in (0, 0.275, 0.55)
                        for x in (0, 0.275, 0.55)
                    ]
                for x0, y0, x1, y1 in tiles:
                    crop = rotated[y0:y1, x0:x1]
                    ch, cw = crop.shape[:2]
                    factor = min(1, 1280 / max(cw, ch))
                    frame = self.cv2.resize(
                        crop, (max(1, round(cw * factor)), max(1, round(ch * factor)))
                    )
                    with self.lock:
                        self.model.setInputSize((frame.shape[1], frame.shape[0]))
                        _, faces = self.model.detect(
                            self.cv2.cvtColor(frame, self.cv2.COLOR_RGB2BGR)
                        )
                    for face in faces if faces is not None else ():
                        fx, fy, fw, fh = map(float, face[:4])
                        score = float(face[-1])
                        corners = [
                            ((x0 + fx / factor) / rw, (y0 + fy / factor) / rh),
                            (
                                (x0 + (fx + fw) / factor) / rw,
                                (y0 + (fy + fh) / factor) / rh,
                            ),
                        ]

                        def inverse(x, y):
                            return ((x, y), (1 - y, x), (1 - x, 1 - y), (y, 1 - x))[
                                rotation
                            ]

                        points = [inverse(x, y) for x, y in corners]
                        xs, ys = zip(*points)
                        left, top = max(0, min(xs)), max(0, min(ys))
                        right, bottom = min(1, max(xs)), min(1, max(ys))
                        if right > left and bottom > top:
                            candidates.append(
                                ((left, top, right - left, bottom - top), score)
                            )
            unique = []
            for box, score in sorted(candidates, key=lambda c: -c[1]):
                if not any(same_face(box, old) for old, _ in unique):
                    unique.append((box, score))
            result = []
            for index, (box, score) in enumerate(unique):
                x, y, w, h = box
                left = max(0, x - 0.08 * w)
                top = max(0, y - 0.12 * h)
                padded = (
                    left,
                    top,
                    min(1, x + 1.08 * w) - left,
                    min(1, y + 1.12 * h) - top,
                )
                ref = source_ref
                if placement is not None:
                    px, py, pw, ph = placement
                    padded = (
                        px + padded[0] * pw,
                        py + padded[1] * ph,
                        padded[2] * pw,
                        padded[3] * ph,
                    )
                if source_ref.startswith(("docx:", "pptx:")):
                    ref = f"{source_ref}:face:{index}"
                location = SourceLocation(
                    artifact_id=artifact_id,
                    kind="face",
                    page_number=page_number,
                    slide_number=slide_number,
                    source_ref=ref,
                    start=None,
                    end=None,
                    bbox=padded,
                )
                result.append(
                    DetectionCandidate(
                        rule_id="FACE",
                        category="biometric",
                        confidence=score,
                        recognizer_confidence=score,
                        recognizer="SparkTiledYuNet",
                        location=location,
                    )
                )
            return result
        except Exception:
            raise ProcessingError(
                ProcessingErrorCode.FACE_DETECTION_FAILED,
                "Face detection could not complete.",
                artifact_id=artifact_id,
            ) from None
