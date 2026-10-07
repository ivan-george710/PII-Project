from pathlib import Path

from app.engines.extraction import ExtractionEngine


PDF_PATH = Path(
    r"C:\Users\ivang\Optiv\Cadence_Group_Risk_Management_Policy__v6.0.pdf"
)


def main():
    engine = ExtractionEngine()

    result = engine.extract(PDF_PATH)

    print("========== EXTRACTION ==========")
    print(f"File: {result.filename}")
    print(f"Pages: {len(result.pages)}")

    for page in result.pages:
        print(
            f"Page {page.page_number}: "
            f"{page.extraction_method}"
        )

    print()
    print(result.full_text)


if __name__ == "__main__":
    main()