"""Small format dispatcher sharing the existing ArtifactResult contract."""
from .artifacts import OfficeArtifactEngine


class DocumentArtifactEngine:
    def __init__(self, output_dir=None):
        self.office=OfficeArtifactEngine(output_dir)
        self.output_dir=output_dir

    def _engine(self, extraction):
        if extraction.file_type=="pdf":
            from .pdf_artifacts import PDFArtifactEngine
            return PDFArtifactEngine(self.output_dir)
        return self.office

    def redact(self, extraction, detection, redaction):
        return self._engine(extraction).redact(extraction,detection,redaction)

    def verify(self, extraction, redaction, result):
        return self._engine(extraction).verify(extraction,redaction,result)
