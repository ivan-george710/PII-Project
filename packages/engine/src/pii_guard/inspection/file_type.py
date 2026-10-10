from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID
from zipfile import BadZipFile, ZipFile

from pii_guard.errors import ProcessingError, ProcessingErrorCode


MAX_ARTIFACT_BYTES = 25 * 1024 * 1024
MAX_PACKAGE_EXPANDED_BYTES = 100 * 1024 * 1024

FileFormat = Literal["pdf", "docx", "pptx", "png", "jpeg"]


@dataclass(frozen=True)
class DetectedFile:
    path: Path
    file_format: FileFormat
    mime_type: str
    size_bytes: int


def detect_file_type(
    path: Path, *, artifact_id: UUID | None = None,
    max_bytes: int = MAX_ARTIFACT_BYTES,
    max_package_bytes: int = MAX_PACKAGE_EXPANDED_BYTES,
) -> DetectedFile:
    try:
        return _detect_file_type(path, artifact_id=artifact_id, max_bytes=max_bytes, max_package_bytes=max_package_bytes)
    except ProcessingError:
        raise
    except Exception as exc:
        raise ProcessingError(ProcessingErrorCode.EXTRACTION_FAILED, "Artifact source could not be inspected.", artifact_id=artifact_id) from exc


def _detect_file_type(
    path: Path,
    *,
    artifact_id: UUID | None = None,
    max_bytes: int = MAX_ARTIFACT_BYTES,
    max_package_bytes: int = MAX_PACKAGE_EXPANDED_BYTES,
) -> DetectedFile:
    if not path.exists():
        raise ProcessingError(
            ProcessingErrorCode.UNSUPPORTED_FILE,
            "Artifact source file does not exist.",
            artifact_id=artifact_id,
        )
    if not path.is_file():
        raise ProcessingError(
            ProcessingErrorCode.UNSUPPORTED_FILE,
            "Artifact source path is not a regular file.",
            artifact_id=artifact_id,
        )

    size_bytes = path.stat().st_size
    if size_bytes <= 0:
        raise ProcessingError(
            ProcessingErrorCode.UNSUPPORTED_FILE,
            "Empty files are not supported.",
            artifact_id=artifact_id,
        )
    if size_bytes > max_bytes:
        raise ProcessingError(
            ProcessingErrorCode.UNSUPPORTED_FILE,
            "Artifact exceeds the supported size limit.",
            artifact_id=artifact_id,
        )

    with path.open("rb") as source:
        header = source.read(16)
    if header.startswith(b"%PDF-"):
        return DetectedFile(path, "pdf", "application/pdf", size_bytes)
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return DetectedFile(path, "png", "image/png", size_bytes)
    if header.startswith(b"\xff\xd8\xff"):
        return DetectedFile(path, "jpeg", "image/jpeg", size_bytes)
    if header.startswith(b"PK\x03\x04"):
        return _detect_open_xml(path, size_bytes, artifact_id=artifact_id, max_package_bytes=max_package_bytes)

    raise ProcessingError(
        ProcessingErrorCode.UNSUPPORTED_FILE,
        "Unsupported file type.",
        artifact_id=artifact_id,
    )


def _detect_open_xml(
    path: Path,
    size_bytes: int,
    *,
    artifact_id: UUID | None,
    max_package_bytes: int,
) -> DetectedFile:
    try:
        with ZipFile(path) as archive:
            if any(info.flag_bits & 1 for info in archive.infolist()):
                raise ProcessingError(ProcessingErrorCode.ENCRYPTED_FILE, "Encrypted packages are not supported.", artifact_id=artifact_id)
            if sum(info.file_size for info in archive.infolist()) > max_package_bytes:
                raise ProcessingError(ProcessingErrorCode.UNSUPPORTED_FILE, "Expanded document package exceeds the supported size limit.", artifact_id=artifact_id)
            names = set(archive.namelist())
    except BadZipFile as exc:
        raise ProcessingError(
            ProcessingErrorCode.UNSUPPORTED_FILE,
            "Malformed OpenXML package.",
            artifact_id=artifact_id,
        ) from exc

    if "word/document.xml" in names:
        return DetectedFile(
            path,
            "docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size_bytes,
        )
    if "ppt/presentation.xml" in names:
        return DetectedFile(
            path,
            "pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            size_bytes,
        )

    raise ProcessingError(
        ProcessingErrorCode.UNSUPPORTED_FILE,
        "Unsupported ZIP-based document type.",
        artifact_id=artifact_id,
    )
