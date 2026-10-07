from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dataclasses import dataclass
from pathlib import Path

@dataclass
class ExtractedPage:
    """
    Text extracted from one logical page of a document.
    """

    page_number: int
    text: str
    extraction_method: str


@dataclass
class ExtractionResult:
    """
    Normalized extraction output passed to downstream engines.
    """

    source_path: Path
    filename: str
    file_type: str
    pages: list[ExtractedPage]

    @property
    def full_text(self) -> str:
        """
        Combine page text while preserving page boundaries.
        """
        return "\n\n".join(
            page.text for page in self.pages
        )

@dataclass
class OCRTextBlock:
    text: str
    confidence: float
    bounding_box: list[list[float]]


@dataclass
class ExtractedPage:
    page_number: int
    text: str
    extraction_method: str
    blocks: list[OCRTextBlock] | None = None


@dataclass
class ExtractionResult:
    source_path: Path
    filename: str
    file_type: str
    pages: list[ExtractedPage]

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)