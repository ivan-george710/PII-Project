from pathlib import Path

from app.engines.file_intelligence import FileIntelligenceEngine

from .models import ExtractionResult
from .ocr import OCREngine
from .pdf import extract_text_pdf


class ExtractionEngine:
    """Routes documents to the appropriate extraction strategy."""

    def __init__(self):
        self.file_intelligence = FileIntelligenceEngine()
        self.ocr_engine = OCREngine()

    def extract(self, file_path: str | Path) -> ExtractionResult:
        path = Path(file_path)

        metadata = self.file_intelligence.analyze(str(path))

        if metadata.file_type == "pdf":
            return self._extract_pdf(path, metadata.extraction_strategy)

        if metadata.file_type == "docx":
            from .docx import extract_docx
            return self._extract_media(extract_docx(path))

        if metadata.file_type == "pptx":
            from .pptx import extract_pptx
            return self._extract_media(extract_pptx(path))

        if metadata.file_type == "image":
            from .models import ExtractedPage
            from app.engines.visual_detection.images import decode
            from tempfile import TemporaryDirectory
            with decode(path.read_bytes(), 'display') as image, TemporaryDirectory() as directory:
                rendered = Path(directory) / 'image.png'
                image.save(rendered)
                blocks = self.ocr_engine.extract_image(rendered)
            return ExtractionResult(path, path.name, 'image',
                [ExtractedPage(1, '\n'.join(b.text for b in blocks), 'ocr', blocks)])

        raise NotImplementedError(
            f"Extraction for '{metadata.file_type}' "
            "is not implemented yet."
        )

    def _extract_pdf(
        self,
        path: Path,
        strategy: str,
    ) -> ExtractionResult:

        if strategy == "text":
            return self._extract_hybrid_pdf(path)

        if strategy == "ocr":
            return self.ocr_engine.extract_pdf(path)

        if strategy == "hybrid":
            return self._extract_hybrid_pdf(path)

        raise ValueError(
            f"Unknown PDF extraction strategy: {strategy}"
        )

    def _extract_hybrid_pdf(
    self,
    path: Path,
) -> ExtractionResult:

        from .pdf import extract_hybrid_pdf

        return extract_hybrid_pdf(
        path,
        self.ocr_engine,
    )

    def _extract_media(self, extraction):
        from .media import extract_media
        return extract_media(extraction, self.ocr_engine)
