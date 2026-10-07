from pathlib import Path

from reportlab.pdfgen import canvas

from app.engines.extraction.pdf import extract_text_pdf


def create_text_pdf(path: Path):
    pdf = canvas.Canvas(str(path))

    pdf.drawString(
        100,
        700,
        "Cadence Financial Group",
    )

    pdf.drawString(
        100,
        680,
        "Risk Management Policy",
    )

    pdf.showPage()
    pdf.save()


def test_extract_text_pdf(tmp_path):
    test_file = tmp_path / "test.pdf"

    create_text_pdf(test_file)

    result = extract_text_pdf(test_file)

    assert result.file_type == "pdf"
    assert result.filename == "test.pdf"
    assert len(result.pages) == 1

    assert "Cadence Financial Group" in result.pages[0].text
    assert "Risk Management Policy" in result.pages[0].text

    assert result.pages[0].page_number == 1
    assert result.pages[0].extraction_method == "text"