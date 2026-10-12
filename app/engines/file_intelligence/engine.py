from os import path
from pathlib import Path

from .detector import detect_file_type
from .models import FileMetadata
from .pdf_analyzer import analyze_pdf


class FileIntelligenceEngine:
    """
    Engine responsible for validating an input artifact,
    identifying its type, and selecting the extraction strategy.
    """

    def analyze(self, file_path: str) -> FileMetadata:

        path = Path(file_path)

        # Validate that the path exists.
        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        # Validate that the path points to a file.
        if not path.is_file():
            raise ValueError(
                f"Path is not a file: {file_path}"
            )

        # Detect file type and MIME type.
        file_type, mime_type = detect_file_type(path)

        # Select the downstream extraction strategy.
        if file_type == "pdf":
            pdf_analysis = analyze_pdf(path)
            strategy = pdf_analysis["extraction_strategy"]

        elif file_type == "image":
            strategy = "ocr"

        elif file_type == "docx":
            strategy = "docx"

        elif file_type == "pptx":
            strategy = "pptx"

        else:
            raise ValueError(
                f"No extraction strategy available for: {file_type}"
            )

        metadata = FileMetadata(
        path=path,
        filename=path.name,
        extension=path.suffix.lower(),
        mime_type=mime_type,
        file_type=file_type,
        extraction_strategy=strategy,
)

        if file_type == "pdf":
            metadata.total_pages = pdf_analysis["total_pages"]
            metadata.text_pages = pdf_analysis["text_pages"]
            metadata.image_only_pages = pdf_analysis["image_only_pages"]
            metadata.mixed_pages = pdf_analysis["mixed_pages"]
            metadata.blank_pages = pdf_analysis["blank_pages"]
            metadata.requires_ocr = pdf_analysis["requires_ocr"]

        return metadata