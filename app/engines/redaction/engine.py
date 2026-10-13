"""Local text redaction; does not run detection, inference, or file mutation."""
from copy import deepcopy
from math import isfinite
from pathlib import Path
import re
from typing import TYPE_CHECKING

from .models import (RedactedPage, RedactionIssue, RedactionRecord,
                     RedactionResult, RedactionValidationError)
from .resolver import resolve_overlaps
from .tagging import Tagger

if TYPE_CHECKING:
    from app.engines.extraction.models import ExtractionResult
    from app.engines.pii_detection.models import PIIDetectionResult


def _decision(detection, collection):
    # Collection membership is Engine 3's legacy final decision when metadata
    # is absent. Explicit metadata always takes precedence; REVIEW never vanishes.
    validation = detection.validation_decision
    llm = detection.llm_decision
    final = getattr(detection, "final_decision", None)
    if final is not None and final != collection:
        return "UNKNOWN"
    valid = {None, "CONFIRM", "REJECT", "AMBIGUOUS", "REVIEW"}
    if validation not in valid or llm not in {None, "CONFIRM", "REJECT", "REVIEW"}:
        return "UNKNOWN"
    if collection == "REVIEW" or llm == "REVIEW" or validation == "REVIEW":
        return "REVIEW"
    if validation in {"CONFIRM", "REJECT"} and llm is not None and llm != validation:
        return "UNKNOWN"
    if llm is not None:
        decision = llm
    elif validation == "AMBIGUOUS":
        return "REVIEW"
    else:
        decision = validation or collection
    if decision != collection:
        return "UNKNOWN"
    return decision


class RedactionEngine:
    def redact(self, extraction_result: "ExtractionResult",
               pii_detection_result: "PIIDetectionResult") -> RedactionResult:
        if extraction_result is None or pii_detection_result is None:
            raise RedactionValidationError("Extraction and detection results are required")
        extraction, detection_result = extraction_result, pii_detection_result
        if (Path(extraction.source_path).resolve() != Path(detection_result.source_path).resolve()
                or extraction.filename != detection_result.filename):
            raise RedactionValidationError("Source document mismatch")
        pages = {}
        for page in extraction.pages:
            if (type(page.page_number) is not int or page.page_number <= 0
                    or page.page_number in pages or not isinstance(page.text, str)):
                raise RedactionValidationError("Invalid or duplicate extracted page")
            pages[page.page_number] = page
        result = RedactionResult(Path(extraction.source_path), extraction.filename, [])
        confirmed = {number: [] for number in pages}
        for collection, records in (("CONFIRM", detection_result.detections),
                                    ("REJECT", detection_result.rejected),
                                    ("REVIEW", getattr(detection_result, "review", []))):
            for original in records:
                d = deepcopy(original)  # Audit snapshots must not alias caller objects.
                if type(d.page_number) is not int or d.page_number not in pages:
                    raise RedactionValidationError("Detection references invalid page")
                page = pages[d.page_number]
                if (type(d.start) is not int or type(d.end) is not int
                        or not 0 <= d.start < d.end <= len(page.text)):
                    raise RedactionValidationError(f"Invalid offsets on page {d.page_number}")
                if page.text[d.start:d.end] != d.text:
                    raise RedactionValidationError(f"Detection text mismatch on page {d.page_number}")
                if (not isinstance(d.entity_type, str)
                        or not re.fullmatch(r"[A-Z][A-Z0-9_]*", d.entity_type)
                        or not isinstance(d.confidence, (float, int))
                        or isinstance(d.confidence, bool) or not isfinite(d.confidence)
                        or not 0 <= d.confidence <= 1):
                    raise RedactionValidationError("Invalid entity type or confidence")
                if d.source_block is not None:
                    if (type(d.source_block) is not int or page.blocks is None
                            or not 0 <= d.source_block < len(page.blocks)):
                        raise RedactionValidationError("Invalid source block reference")
                decision = _decision(d, collection)
                if decision == "CONFIRM":
                    confirmed[d.page_number].append(d)
                elif decision == "REJECT":
                    result.rejected.append(d)
                else:
                    if decision == "REVIEW":
                        confirmed[d.page_number].append(d)
                    result.issues.append(RedactionIssue(
                        "review_required" if decision == "REVIEW" else "unknown_decision",
                        d.page_number, d))
        tagger = Tagger()
        for page in extraction.pages:
            selected, issues = resolve_overlaps(confirmed[page.page_number])
            result.issues.extend(issues)
            replacements = []
            shift = 0
            for d in selected:
                tag = tagger.tag(d.entity_type, d.text)
                replacements.append((d, tag))
                result.tag_mapping.setdefault(tag, []).append(d)
                redacted_start = d.start + shift
                result.redactions.append(RedactionRecord(
                    d.entity_type, tag, d.text, d.page_number, d.start, d.end,
                    redacted_start, redacted_start + len(tag), d.confidence,
                    d.recognizer, d.detection_method, d.validation_decision,
                    d.llm_decision, page.extraction_method, d.source_block))
                shift += len(tag) - (d.end - d.start)
            text = page.text
            for d, tag in reversed(replacements):
                text = text[:d.start] + tag + text[d.end:]
            result.pages.append(RedactedPage(page.page_number, text, page.extraction_method))
        return result
