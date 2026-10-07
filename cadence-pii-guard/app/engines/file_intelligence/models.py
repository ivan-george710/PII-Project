from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FileMetadata:
    """
    Normalized metadata describing an input artifact.

    This object is passed from the File Intelligence Engine
    to the Extraction Engine.
    """

    path: Path
    filename: str
    extension: str
    mime_type: str
    file_type: str
    extraction_strategy: str

    is_scanned: Optional[bool] = None

    total_pages: Optional[int] = None
    text_pages: Optional[int] = None
    image_only_pages: Optional[int] = None
    mixed_pages: Optional[int] = None
    blank_pages: Optional[int] = None
    requires_ocr: Optional[bool] = None