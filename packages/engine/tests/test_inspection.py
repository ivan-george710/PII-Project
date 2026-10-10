from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.inspection import analyze_pdf, detect_file_type
from pypdf import PdfWriter
from zipfile import ZipFile, ZIP_DEFLATED
from uuid import uuid4


def _write_text_pdf(path: Path, text: str = "Native PDF text") -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.drawString(72, 720, text)
    pdf.showPage()
    pdf.save()


def _write_image(path: Path) -> None:
    image = Image.new("RGB", (200, 100), "white")
    image.save(path)


def _write_image_pdf(path: Path, image_path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.drawImage(str(image_path), 72, 500, width=200, height=100)
    pdf.showPage()
    pdf.save()


def test_detect_file_type_uses_content_not_extension(tmp_path: Path) -> None:
    path = tmp_path / "looks-like.pdf"
    image = Image.new("RGB", (200, 100), "white")
    image.save(path, format="JPEG")

    detected = detect_file_type(path)

    assert detected.file_format == "jpeg"
    assert detected.mime_type == "image/jpeg"


def test_detect_file_type_rejects_unsupported_content(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("hello", encoding="utf-8")

    with pytest.raises(ProcessingError) as error:
        detect_file_type(path)

    assert error.value.code is ProcessingErrorCode.UNSUPPORTED_FILE


def test_detect_file_type_rejects_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.pdf"
    path.write_bytes(b"")

    with pytest.raises(ProcessingError) as error:
        detect_file_type(path)

    assert error.value.code is ProcessingErrorCode.UNSUPPORTED_FILE


def test_analyze_pdf_classifies_native_scanned_and_mixed_pages(tmp_path: Path) -> None:
    image_path = tmp_path / "scan.jpg"
    _write_image(image_path)

    native_pdf = tmp_path / "native.pdf"
    _write_text_pdf(native_pdf)
    native = analyze_pdf(native_pdf)
    assert native.extraction_strategy == "text"
    assert native.text_pages == 1
    assert native.requires_ocr is False

    scanned_pdf = tmp_path / "scanned.pdf"
    _write_image_pdf(scanned_pdf, image_path)
    scanned = analyze_pdf(scanned_pdf)
    assert scanned.extraction_strategy == "ocr"
    assert scanned.image_only_pages == 1
    assert scanned.requires_ocr is True

    mixed_pdf = tmp_path / "mixed.pdf"
    pdf = canvas.Canvas(str(mixed_pdf), pagesize=letter)
    pdf.drawString(72, 720, "Page one native")
    pdf.showPage()
    pdf.drawImage(str(image_path), 72, 500, width=200, height=100)
    pdf.showPage()
    pdf.save()

    mixed = analyze_pdf(mixed_pdf)
    assert mixed.extraction_strategy == "hybrid"
    assert mixed.text_pages == 1
    assert mixed.image_only_pages == 1
    assert mixed.requires_ocr is True


def test_analyze_pdf_marks_same_page_native_and_image_as_ocr_required(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "scan.jpg"
    _write_image(image_path)
    pdf_path = tmp_path / "mixed-page.pdf"
    pdf = canvas.Canvas(str(pdf_path), pagesize=letter)
    pdf.drawString(72, 720, "Native and image on one page")
    pdf.drawImage(str(image_path), 72, 500, width=200, height=100)
    pdf.showPage()
    pdf.save()

    analysis = analyze_pdf(pdf_path)

    assert analysis.extraction_strategy == "hybrid"
    assert analysis.mixed_pages == 1
    assert analysis.pages[0].requires_ocr is True


def test_analyze_pdf_rejects_malformed_pdf(tmp_path: Path) -> None:
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"%PDF-1.7\nnot a valid pdf")

    with pytest.raises(ProcessingError) as error:
        analyze_pdf(path)

    assert error.value.code is ProcessingErrorCode.EXTRACTION_FAILED


def test_encrypted_pdf_has_distinct_error(tmp_path: Path) -> None:
    path = tmp_path / "encrypted.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=100)
    writer.encrypt("private-password")
    writer.write(path)
    identity = uuid4()
    with pytest.raises(ProcessingError) as error:
        analyze_pdf(path, artifact_id=identity)
    assert error.value.code == ProcessingErrorCode.ENCRYPTED_FILE
    assert error.value.artifact_id == identity
    assert "private-password" not in str(error.value)


def test_pdf_page_limit_configurable(tmp_path: Path) -> None:
    path = tmp_path / "pages.pdf"
    writer = PdfWriter()
    for _ in range(2):
        writer.add_blank_page(width=200, height=100)
    writer.write(path)
    with pytest.raises(ProcessingError) as error:
        analyze_pdf(path, max_pages=1)
    assert error.value.code == ProcessingErrorCode.UNSUPPORTED_FILE
    assert analyze_pdf(path, max_pages=2).blank_pages == 2


def test_compressed_office_expansion_limit(tmp_path: Path) -> None:
    path = tmp_path / "compressed.docx"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", "x" * 10000)
    assert path.stat().st_size < 1000
    with pytest.raises(ProcessingError) as error:
        detect_file_type(path, max_package_bytes=1000)
    assert error.value.code == ProcessingErrorCode.UNSUPPORTED_FILE
    assert detect_file_type(path, max_package_bytes=10000).file_format == "docx"


@pytest.mark.parametrize("kind", ["missing", "directory", "oversize", "badzip"])
def test_source_file_safeguards(tmp_path: Path, kind: str) -> None:
    path = tmp_path / "source"
    if kind == "directory":
        path.mkdir()
    elif kind == "oversize":
        path.write_bytes(b"%PDF-1.7" + b"x" * 20)
    elif kind == "badzip":
        path.write_bytes(b"PK\x03\x04invalid")
    with pytest.raises(ProcessingError) as error:
        detect_file_type(path, max_bytes=16)
    assert error.value.code == ProcessingErrorCode.UNSUPPORTED_FILE
