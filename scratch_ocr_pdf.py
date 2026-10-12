from pathlib import Path

from app.engines.extraction.ocr import OCREngine


PDF_PATH = Path(
    r"C:\Users\ivang\Optiv\Cadence_Group_Risk_Management_Policy__v6.0.pdf"
)


def main():
    print("Starting OCR extraction...")

    engine = OCREngine()

    result = engine.extract_pdf(PDF_PATH)

    print()
    print("========== EXTRACTION COMPLETE ==========")
    print(f"File: {result.filename}")
    print(f"Pages: {len(result.pages)}")
    print()

    for page in result.pages:
        print(
            f"Page {page.page_number}: "
            f"{len(page.blocks or [])} OCR blocks, "
            f"{len(page.text)} characters"
        )

    print()
    print("========== FIRST PAGE ==========")
    print(result.pages[0].text)


if __name__ == "__main__":
    main()