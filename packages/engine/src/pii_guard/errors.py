from __future__ import annotations

from enum import StrEnum
from uuid import UUID


class ProcessingErrorCode(StrEnum):
    UNSUPPORTED_FILE = "UNSUPPORTED_FILE"
    ENCRYPTED_FILE = "ENCRYPTED_FILE"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    OCR_FAILED = "OCR_FAILED"
    FACE_DETECTION_FAILED = "FACE_DETECTION_FAILED"
    REDACTION_FAILED = "REDACTION_FAILED"
    INVALID_POLICY = "INVALID_POLICY"
    PROCESSING_TIMEOUT = "PROCESSING_TIMEOUT"


class ProcessingError(Exception):
    def __init__(
        self,
        code: ProcessingErrorCode,
        message: str,
        *,
        submission_id: UUID | None = None,
        artifact_id: UUID | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.submission_id = submission_id
        self.artifact_id = artifact_id

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"
