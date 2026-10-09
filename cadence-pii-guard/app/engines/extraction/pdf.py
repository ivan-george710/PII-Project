from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

from .models import ExtractedPage, ExtractionResult


def _open_pdf(path: Path) -> PdfReader:
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise ValueError(f"PDF is password-protected: {path.name}")
        if not reader.pages:
            raise ValueError(f"PDF contains no pages: {path.name}")
    except FileNotDecryptedError as error:
        raise ValueError(
            f"PDF is password-protected: {path.name}"
        ) from error
    except (PdfReadError, EOFError) as error:
        raise ValueError(
            f"Could not read PDF '{path.name}': {error}"
        ) from error

    return reader


def extract_text_pdf(path: Path) -> ExtractionResult:
    """
    Extract selectable text from a text-based PDF.
    """

    reader = _open_pdf(path)

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

    reader = _open_pdf(path)

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