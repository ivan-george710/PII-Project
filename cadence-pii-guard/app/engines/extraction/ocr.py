from pathlib import Path
from tempfile import TemporaryDirectory

from pdf2image import convert_from_path
from rapidocr_onnxruntime import RapidOCR

from .models import ExtractedPage, ExtractionResult, OCRTextBlock
from .pdf import _open_pdf


class OCREngine:
    """OCR engine backed by RapidOCR ONNX Runtime."""

    def __init__(self):
        self.engine = RapidOCR()

    def extract_image(self, image_path: Path) -> list[OCRTextBlock]:
        results, _ = self.engine(str(image_path))

        if not results:
            return []

        blocks = []

        for item in results:
            bounding_box, text, confidence = item

            blocks.append(
                OCRTextBlock(
                    text=str(text),
                    confidence=float(confidence),
                    bounding_box=bounding_box,
                )
            )

        return blocks

    def extract_image_file(
        self,
        image_path: Path,
        file_type: str,
    ) -> ExtractionResult:
        blocks = self.extract_image(image_path)
        page_text = "\n".join(block.text for block in blocks)
        return ExtractionResult(
            source_path=image_path,
            filename=image_path.name,
            file_type=file_type,
            pages=[
                ExtractedPage(
                    page_number=1,
                    text=page_text,
                    extraction_method="ocr",
                    blocks=blocks,
                )
            ],
        )

    def extract_pdf(
        self,
        pdf_path: Path,
        dpi: int = 150,
    ) -> ExtractionResult:

        reader = _open_pdf(pdf_path)
        total_pages = len(reader.pages)

        pages = []

        print(f"OCR extraction: {total_pages} pages", flush=True)

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            for page_number in range(1, total_pages + 1):

                print(
                    f"Processing page {page_number}/{total_pages}...",
                    flush=True,
                )

                images = convert_from_path(
                    str(pdf_path),
                    dpi=dpi,
                    first_page=page_number,
                    last_page=page_number,
                    output_folder=str(temp_path),
                    fmt="png",
                )

                if not images:
                    print(
                        f"Warning: page {page_number} produced no image; "
                        "retaining an empty OCR page",
                        flush=True,
                    )
                    pages.append(
                        ExtractedPage(
                            page_number=page_number,
                            text="",
                            extraction_method="ocr",
                            blocks=[],
                        )
                    )
                    continue

                image_path = temp_path / f"page-{page_number}.png"
                images[0].save(image_path)

                blocks = self.extract_image(image_path)

                page_text = "\n".join(
                    block.text
                    for block in blocks
                )

                pages.append(
                    ExtractedPage(
                        page_number=page_number,
                        text=page_text,
                        extraction_method="ocr",
                        blocks=blocks,
                    )
                )

                images[0].close()
                image_path.unlink(missing_ok=True)

                print(
                    f"  ✓ {len(blocks)} OCR blocks, "
                    f"{len(page_text)} characters",
                    flush=True,
                )

        return ExtractionResult(
            source_path=pdf_path,
            filename=pdf_path.name,
            file_type="pdf",
            pages=pages,
        )
    def extract_pdf_page(
    self,
    pdf_path: Path,
    page_number: int,
    dpi: int = 150,
) -> ExtractedPage:
        """Render and OCR a single PDF page."""

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            images = convert_from_path(
                str(pdf_path),
                dpi=dpi,
                first_page=page_number,
                last_page=page_number,
                output_folder=str(temp_path),
                fmt="png",
        )

            if not images:
                raise ValueError(
                    f"Could not render PDF page {page_number}"
            )

            image_path = temp_path / f"page-{page_number}.png"
            images[0].save(image_path)

            blocks = self.extract_image(image_path)

            page_text = "\n".join(
                block.text
                for block in blocks
        )

            images[0].close()

        return ExtractedPage(
            page_number=page_number,
            text=page_text,
            extraction_method="ocr",
            blocks=blocks,
        )