from pathlib import Path

from app.engines.extraction import ExtractionEngine


PDF_PATH = Path(r"tests\fixtures\hybrid.pdf")


def main():
    engine = ExtractionEngine()

    result = engine.extract(PDF_PATH)

    print("========== HYBRID EXTRACTION ==========")
    print(f"File: {result.filename}")
    print(f"Pages: {len(result.pages)}")
    print()

    for page in result.pages:
        print(
            f"Page {page.page_number}: "
            f"{page.extraction_method}"
        )
        print(page.text)
        print()


if __name__ == "__main__":
    main()