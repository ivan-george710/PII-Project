from pathlib import Path

from pypdf import PdfReader

from .models import ExtractedPage, ExtractionResult


def extract_text_pdf(path: Path) -> ExtractionResult:
    """
    Extract selectable text from a text-based PDF.
    """

    reader = PdfReader(str(path))

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        pages.append(
            ExtractedPage(
                page_number=page_number,
                text=text.strip(),
                extraction_method="text",
            )
        )

    return ExtractionResult(
        source_path=path,
        filename=path.name,
        file_type="pdf",
        pages=pages,
    )
def extract_hybrid_pdf(
    path: Path,
    ocr_engine,
) -> ExtractionResult:
    """Extract each PDF page using text extraction or OCR as required."""

    reader = PdfReader(str(path))

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):

        text = page.extract_text() or ""

        if text.strip():
            pages.append(
                ExtractedPage(
                    page_number=page_number,
                    text=text.strip(),
                    extraction_method="text",
                )
            )
        else:
            ocr_result = ocr_engine.extract_pdf_page(
                path,
                page_number,
            )

            pages.append(ocr_result)

    return ExtractionResult(
        source_path=path,
        filename=path.name,
        file_type="pdf",
        pages=pages,
    )