from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class OCRTextBlock:
    text: str
    confidence: float
    bounding_box: list[list[float]]


@dataclass
class SourceTextNode:
    path: str
    start: int
    end: int
    kind: str = "text"


@dataclass
class SourceSegment:
    page_number: int
    part: str
    paragraph_path: str
    start: int
    end: int
    nodes: list[SourceTextNode]
    location: dict = field(default_factory=dict)


@dataclass
class StructureMap:
    source_sha256: str
    location_kind: str
    segments: list[SourceSegment]
    limitations: dict[str, int] = field(default_factory=dict)


def restore_structure(data):
    if data is None:
        return None
    return StructureMap(data["source_sha256"], data["location_kind"], [
        SourceSegment(s["page_number"], s["part"], s["paragraph_path"], s["start"], s["end"],
                      [SourceTextNode(**n) for n in s["nodes"]], s["location"])
        for s in data["segments"]], data["limitations"])


@dataclass
class ExtractedPage:
    page_number: int
    text: str
    extraction_method: str
    blocks: list[OCRTextBlock] | None = None


@dataclass
class PDFSourceMap:
    source_sha256: str
    ocr_dpi_by_page: dict[str, int] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    source_path: Path
    filename: str
    file_type: str
    pages: list[ExtractedPage]
    structure: StructureMap | None = None
    pdf_source: PDFSourceMap | None = None
    visual: object | None = None  # Cadence VisualInspection; immutable original audit evidence.

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)
