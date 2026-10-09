from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from .models import ExtractedPage, ExtractionResult


def extract_docx(path: Path) -> ExtractionResult:
    """Extract Word paragraphs and tables into one normalized page."""
    document = Document(path)
    text_parts: list[str] = []

    for item in document.iter_inner_content():
        if isinstance(item, Paragraph):
            text = item.text.strip()
            if text:
                text_parts.append(text)
        elif isinstance(item, Table):
            for row in item.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if any(cells):
                    text_parts.append("\t".join(cells))

    return ExtractionResult(
        source_path=path,
        filename=path.name,
        file_type="docx",
        pages=[
            ExtractedPage(
                page_number=1,
                text="\n".join(text_parts),
                extraction_method="text",
            )
        ],
    )