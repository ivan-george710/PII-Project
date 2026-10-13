from pathlib import Path

from pypdf import PdfReader


def _has_extractable_text(page) -> bool:
    """
    Determine whether a PDF page contains meaningful
    extractable text.
    """
    text = page.extract_text()

    if not text:
        return False

    return bool(text.strip())


def _has_images(page) -> bool:
    """
    Determine whether a PDF page contains embedded images.
    """
    try:
        return len(page.images) > 0
    except Exception:
        return False


def analyze_pdf(path: Path) -> dict:
    """
    Inspect a PDF and determine whether its pages require
    normal text extraction, OCR, or a hybrid approach.
    """

    reader = PdfReader(str(path))

    total_pages = len(reader.pages)
    text_pages = 0
    image_only_pages = 0
    mixed_pages = 0
    blank_pages = 0

    for page in reader.pages:
        has_text = _has_extractable_text(page)
        has_images = _has_images(page)

        if has_text and has_images:
            mixed_pages += 1
        elif has_text:
            text_pages += 1
        elif has_images:
            image_only_pages += 1
        else:
            blank_pages += 1

    if mixed_pages > 0 or (image_only_pages > 0 and text_pages > 0):
        extraction_strategy = "hybrid"
    elif image_only_pages > 0:
        extraction_strategy = "ocr"
    else:
        extraction_strategy = "text"

    return {
        "total_pages": total_pages,
        "text_pages": text_pages,
        "image_only_pages": image_only_pages,
        "mixed_pages": mixed_pages,
        "blank_pages": blank_pages,
        "requires_ocr": image_only_pages > 0 or mixed_pages > 0,
        "extraction_strategy": extraction_strategy,
    }