"""Permanent text, image and supported PDF/Office redaction helpers."""

from pii_guard.redaction.text import RedactedTextBlock, redact_block, redact_text
from pii_guard.redaction.image import ImageRedactionResult, redact_image
from pii_guard.redaction.pdf import redact_pdf, redact_pdf_file
from pii_guard.redaction.docx import redact_docx, redact_docx_file
from pii_guard.redaction.pptx import redact_pptx, redact_pptx_file

__all__ = ["RedactedTextBlock", "redact_block", "redact_text", "ImageRedactionResult",
           "redact_image", "redact_pdf", "redact_pdf_file", "redact_docx", "redact_docx_file",
           "redact_pptx", "redact_pptx_file"]
