from pathlib import Path

from app.engines.file_intelligence import FileIntelligenceEngine
from pypdf.errors import FileNotDecryptedError, PdfReadError

from .docx import extract_docx
from .models import ExtractionResult
from .ocr import OCREngine
from .pdf import extract_hybrid_pdf, extract_text_pdf
from .pptx import extract_pptx


class ExtractionEngine:
    """Routes documents to the appropriate extraction strategy."""

    def __init__(self):
        self.file_intelligence = FileIntelligenceEngine()
        self.ocr_engine = OCREngine()

    def extract(self, file_path: str | Path) -> ExtractionResult:
        path = Path(file_path)

        try:
            metadata = self.file_intelligence.analyze(str(path))
        except FileNotDecryptedError as error:
            raise ValueError(
                f"PDF is password-protected: {path.name}"
            ) from error
        except (PdfReadError, EOFError) as error:
            raise ValueError(
                f"Could not read PDF '{path.name}': {error}"
            ) from error

        if metadata.file_type == "pdf":
            return self._extract_pdf(path, metadata.extraction_strategy)

        if metadata.file_type == "image":
            file_type = (
                "png"
                if metadata.mime_type == "image/png"
                else "jpeg"
            )
            return self.ocr_engine.extract_image_file(path, file_type)

        if metadata.file_type == "docx":
            return extract_docx(path)

        if metadata.file_type == "pptx":
            return extract_pptx(path)

        raise ValueError(f"Unsupported file type: {metadata.file_type}")

    def _extract_pdf(
        self,
        path: Path,
        strategy: str,
    ) -> ExtractionResult:

        if strategy == "text":
            return extract_text_pdf(path)

        if strategy == "ocr":
            return self.ocr_engine.extract_pdf(path)

        if strategy == "hybrid":
            return extract_hybrid_pdf(path, self.ocr_engine)

        raise ValueError(
            f"Unknown PDF extraction strategy: {strategy}"
        )
