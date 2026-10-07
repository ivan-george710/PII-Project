from pathlib import Path

import magic


SUPPORTED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "image/png": "image",
    "image/jpeg": "image",
}


def detect_file_type(path: Path) -> tuple[str, str]:
    """
    Identify a file using its actual contents rather than
    trusting its filename extension.

    Returns:
        tuple[str, str]:
            logical file type and detected MIME type.
    """

    mime_type = magic.from_file(str(path), mime=True)

    if mime_type not in SUPPORTED_MIME_TYPES:
        raise ValueError(
            f"Unsupported file type: {mime_type}"
        )

    file_type = SUPPORTED_MIME_TYPES[mime_type]

    return file_type, mime_type