from __future__ import annotations

from collections.abc import Iterable
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.models import EngineBaseModel, ExtractedTextBlock, SourceLocation
from pii_guard.rules.policy import RedactionTarget


REPLACEMENT = "[REDACTED]"


class RedactedTextBlock(EngineBaseModel):
    """Internal rendered text with provenance in the ORIGINAL offset frame.

    Not an ExtractedTextBlock: original_location does not span sanitized_text.
    No original text is retained in this result.
    """

    sanitized_text: str
    original_location: SourceLocation
    extraction_method: Literal["native_text", "ocr"]
    confidence: Annotated[float, Field(ge=0, le=1)] | None = None


def _source_identity(location: SourceLocation) -> tuple:
    # Existing detectors retain the block's original box, not a character box.
    return (location.artifact_id, location.kind, location.page_number,
            location.slide_number, location.source_ref, location.bbox)


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def redact_text(text: str, targets: Iterable[RedactionTarget] = (), *,
                source: SourceLocation | None = None,
                submission_id: UUID | None = None) -> str:
    """Render one original message or extraction unit using enabled targets only.

    Omit source for message text. Artifact text requires its full original block
    location (start=0, end=len(text)). Every supplied target must belong to this
    unit; callers partition submission targets by source before rendering.
    Findings are deliberately not accepted or mutated here.
    """
    artifact_id = None
    try:
        if not isinstance(text, str):
            raise ValueError("Text must be a string")
        identity = (None, "message", None, None, None, None)
        if source is not None:
            if not isinstance(source, SourceLocation):
                raise ValueError("Invalid source contract")
            original = SourceLocation.model_validate(source.model_dump(warnings=False))
            artifact_id = original.artifact_id
            if original.kind == "face" or original.start != 0 or original.end != len(text):
                raise ValueError("Source must cover the original text unit")
            if original.kind == "message":
                if _source_identity(original) != identity:
                    raise ValueError("Invalid message source")
            else:
                # Enforce the existing block source-ref and OCR-box conventions.
                ExtractedTextBlock(text=text, location=original, extraction_method=original.kind)
                identity = _source_identity(original)

        spans = []
        for target in targets:
            if not isinstance(target, RedactionTarget):
                raise ValueError("Expected an enabled redaction target")
            validated = RedactionTarget.model_validate(target.model_dump(warnings=False))
            location = validated.location
            if _source_identity(location) != identity:
                raise ValueError("Target belongs to a different source")
            start, end = location.start, location.end
            if start is None or end is None or not 0 <= start < end <= len(text):
                raise ValueError("Target span is outside original text")
            spans.append((start, end))

        # Validate the entire target stream before creating any rendered output.
        parts = []
        cursor = 0
        for start, end in _merge_spans(spans):
            parts.extend((text[cursor:start], REPLACEMENT))
            cursor = end
        parts.append(text[cursor:])
        return "".join(parts)
    except Exception:
        # Validation/provider errors can contain raw input values. Do not chain
        # them into an exception that may later be logged by a caller.
        raise ProcessingError(ProcessingErrorCode.REDACTION_FAILED,
            "Text redaction failed: invalid targets or original source.",
            submission_id=submission_id, artifact_id=artifact_id) from None


def redact_block(block: ExtractedTextBlock, targets: Iterable[RedactionTarget] = (), *,
                 submission_id: UUID | None = None) -> RedactedTextBlock:
    """Render a block without mutating it or rebasing original source locations."""
    artifact_id = None
    try:
        if not isinstance(block, ExtractedTextBlock):
            raise ValueError("Invalid extracted block contract")
        original = ExtractedTextBlock.model_validate(block.model_dump(warnings=False))
        artifact_id = original.location.artifact_id
        sanitized = redact_text(original.text, targets, source=original.location,
                                submission_id=submission_id)
        return RedactedTextBlock(sanitized_text=sanitized,
            original_location=original.location, extraction_method=original.extraction_method,
            confidence=original.confidence)
    except ProcessingError:
        raise
    except Exception:
        raise ProcessingError(ProcessingErrorCode.REDACTION_FAILED,
            "Text redaction failed: invalid extraction source.",
            submission_id=submission_id, artifact_id=artifact_id) from None
