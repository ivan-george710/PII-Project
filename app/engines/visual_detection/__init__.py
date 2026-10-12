"""Local visual privacy inspection; text Presidio counts stay separate."""
from .detector import FaceDetector, FaceDetectionError
from .inspection import VisualInspectionEngine

__all__ = ['FaceDetector', 'FaceDetectionError', 'VisualInspectionEngine']
