from importlib.metadata import metadata

from pypdf import PdfWriter
from app.engines.file_intelligence.pdf_analyzer import analyze_pdf
from pathlib import Path

from PIL import Image as PILImage
from pypdf import PdfWriter
from reportlab.pdfgen import canvas

from app.engines.file_intelligence import FileIntelligenceEngine
from app.engines.file_intelligence.pdf_analyzer import analyze_pdf

from app.engines.file_intelligence import FileIntelligenceEngine

def test_fake_pdf_is_rejected(tmp_path):
    test_file = tmp_path / "fake.pdf"
    test_file.write_bytes(b"This is not actually a PDF")

    engine = FileIntelligenceEngine()

    try:
        engine.analyze(str(test_file))
        assert False, "Expected unsupported file to be rejected"
    except ValueError:
        pass
def create_text_pdf(path: Path):
    """Create a PDF containing selectable text."""
    pdf = canvas.Canvas(str(path))
    pdf.drawString(100, 700, "Cadence Financial Group")
    pdf.drawString(100, 680, "Risk Management Policy")
    pdf.save()


def create_image_pdf(path: Path, image_path: Path):
    """Create a PDF containing an image but no selectable text."""
    pdf = canvas.Canvas(str(path))
    pdf.drawImage(str(image_path), 100, 500, width=200, height=100)
    pdf.save()


def create_mixed_pdf(path: Path, image_path: Path):
    """Create a PDF containing one text page and one image-only page."""
    pdf = canvas.Canvas(str(path))

    # Page 1: selectable text
    pdf.drawString(100, 700, "Cadence Financial Group")
    pdf.drawString(100, 680, "Risk Management Policy")
    pdf.showPage()

    # Page 2: image only
    pdf.drawImage(str(image_path), 100, 500, width=200, height=100)
    pdf.save()


def create_test_image(path: Path):
    """Create a simple image fixture."""
    image = PILImage.new("RGB", (400, 200), "white")
    image.save(path)


def test_text_pdf_detection(tmp_path):
    test_file = tmp_path / "text.pdf"

    create_text_pdf(test_file)

    engine = FileIntelligenceEngine()
    metadata = engine.analyze(str(test_file))

    assert metadata.file_type == "pdf"
    assert metadata.mime_type == "application/pdf"
    assert metadata.extraction_strategy == "text"
    assert metadata.total_pages == 1
    assert metadata.text_pages == 1
    assert metadata.image_only_pages == 0
    assert metadata.mixed_pages == 0
    assert metadata.requires_ocr is False


def test_scanned_pdf_detection(tmp_path):
    image_file = tmp_path / "scan.png"
    pdf_file = tmp_path / "scanned.pdf"

    create_test_image(image_file)
    create_image_pdf(pdf_file, image_file)

    engine = FileIntelligenceEngine()
    metadata = engine.analyze(str(pdf_file))

    assert metadata.file_type == "pdf"
    assert metadata.extraction_strategy == "ocr"
    assert metadata.total_pages == 1
    assert metadata.text_pages == 0
    assert metadata.image_only_pages == 1
    assert metadata.mixed_pages == 0
    assert metadata.requires_ocr is True


def test_mixed_pdf_detection(tmp_path):
    image_file = tmp_path / "scan.png"
    pdf_file = tmp_path / "mixed.pdf"

    create_test_image(image_file)
    create_mixed_pdf(pdf_file, image_file)

    engine = FileIntelligenceEngine()
    metadata = engine.analyze(str(pdf_file))

    assert metadata.file_type == "pdf"
    assert metadata.extraction_strategy == "hybrid"
    assert metadata.total_pages == 2
    assert metadata.text_pages == 1
    assert metadata.image_only_pages == 1
    assert metadata.mixed_pages == 0
    assert metadata.requires_ocr is True


def test_fake_pdf_is_rejected(tmp_path):
    test_file = tmp_path / "fake.pdf"
    test_file.write_bytes(b"This is not actually a PDF")

    engine = FileIntelligenceEngine()

    try:
        engine.analyze(str(test_file))
        assert False, "Expected unsupported file to be rejected"
    except ValueError:
        pass