from dataclasses import dataclass
from pathlib import Path

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