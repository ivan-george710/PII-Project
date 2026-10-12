"""Page-local Presidio detection with exactly one disposition per candidate."""
from math import isfinite
from pathlib import Path
import re

from presidio_analyzer import AnalyzerEngine

from app.engines.extraction.models import ExtractionResult
from .models import DetectedPII, PIIDetectionResult, DetectionProcessingError
from .recognizers import EmployeeIdRecognizer
from .validation import ValidationDecision, validate_detection


class PIIDetectionEngine:
    def __init__(self, *, analyzer=None, custom_rules=None) -> None:
        """Injected analyzers are already configured; default analyzer registers IDs once."""
        if analyzer is None:
            try:
                analyzer = AnalyzerEngine()
                analyzer.registry.add_recognizer(EmployeeIdRecognizer())
            except Exception as exc:
                raise DetectionProcessingError(
                    f"Presidio initialization failed ({type(exc).__name__}); check local NLP dependencies"
                ) from None
        self.analyzer = analyzer
        self.custom_rules = list(custom_rules or [])

    def detect(self, extraction_result: ExtractionResult) -> PIIDetectionResult:
        if extraction_result is None:
            raise DetectionProcessingError("Extraction result is required")
        seen_pages = set()
        for page in extraction_result.pages:
            if (type(page.page_number) is not int or page.page_number <= 0
                    or page.page_number in seen_pages or not isinstance(page.text, str)):
                raise DetectionProcessingError("Invalid extraction page number or text")
            seen_pages.add(page.page_number)
        output = PIIDetectionResult(Path(extraction_result.source_path),
                                    extraction_result.filename, [], [])
        for page in extraction_result.pages:
            if not page.text.strip():
                continue
            try:
                raw = list(self.analyzer.analyze(text=page.text, language="en"))
            except Exception as exc:
                raise DetectionProcessingError(
                    f"Presidio analysis failed on page {page.page_number} ({type(exc).__name__})"
                ) from None
            block_spans = self._block_spans(page)
            try:
                candidates = [self._candidate(item, page, block_spans) for item in raw]
            except DetectionProcessingError:
                raise
            except Exception as exc:
                raise DetectionProcessingError(
                    f"Invalid analyzer candidate on page {page.page_number} ({type(exc).__name__})"
                ) from None
            for rule in (self.custom_rules or []):
                pattern = rule.get('pattern', '')
                if not pattern: continue
                is_regex = rule.get('is_regex', False)
                try:
                    regex = re.compile(pattern if is_regex else re.escape(pattern), re.IGNORECASE)
                    for m in regex.finditer(page.text):
                        st, en = m.start(), m.end()
                        if st >= en: continue
                        block = next((idx for idx, b_st, b_en in block_spans if b_st <= st and en <= b_en), None)
                        ent = rule.get('entity_type', 'CUSTOM_BLOCKED')
                        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", ent): ent = 'CUSTOM_BLOCKED'
                        cand = DetectedPII(
                            ent, page.text[st:en], st, en, 1.0, "custom_rule",
                            f"CustomRuleRecognizer:{rule.get('name', 'Rule')}", page.page_number, block
                        )
                        candidates.append(cand)
                except Exception:
                    pass
            output.pages_analyzed.append(page.page_number)
            output.raw_candidate_count += len(candidates)
            # Keep duplicate raw candidates; no overlap removal in Engine 3.
            candidates.sort(key=lambda d: (d.start, d.end, d.entity_type))
            for detection in candidates:
                context = self._build_validation_context(page.text, detection.start, detection.end)
                try:
                    decision, reason = validate_detection(detection, context=context,
                        context_start=min(detection.start, 200))
                except Exception as exc:
                    raise DetectionProcessingError(
                        f"Validation failed on page {page.page_number} ({type(exc).__name__})"
                    ) from None
                if not isinstance(decision, ValidationDecision):
                    raise DetectionProcessingError(
                        f"Unsupported validation decision on page {page.page_number}")
                detection.validation_decision = decision.value
                detection.validation_reason = reason
                final = "REVIEW" if decision == ValidationDecision.AMBIGUOUS else decision.value
                detection.final_decision = final
                {"CONFIRM": output.detections, "REJECT": output.rejected,
                 "REVIEW": output.review}[final].append(detection)
        if output.disposition_count != output.raw_candidate_count:
            raise DetectionProcessingError("Candidate disposition accounting failed")
        return output

    @staticmethod
    def _candidate(item, page, block_spans) -> DetectedPII:
        if (type(item.start) is not int or type(item.end) is not int
                or not 0 <= item.start < item.end <= len(page.text)):
            raise DetectionProcessingError(f"Invalid analyzer offsets on page {page.page_number}")
        if (not isinstance(item.entity_type, str)
                or not re.fullmatch(r"[A-Z][A-Z0-9_]*", item.entity_type)
                or not isinstance(item.score, (float, int)) or isinstance(item.score, bool)
                or not isfinite(item.score) or not 0 <= item.score <= 1):
            raise DetectionProcessingError(
                f"Invalid analyzer entity or confidence on page {page.page_number}")
        metadata = item.recognition_metadata or {}
        if not isinstance(metadata, dict):
            raise DetectionProcessingError(f"Invalid analyzer metadata on page {page.page_number}")
        recognizer = metadata.get("recognizer_name", "unknown")
        if not isinstance(recognizer, str):
            raise DetectionProcessingError(f"Invalid recognizer metadata on page {page.page_number}")
        method = {"SpacyRecognizer": "nlp",
                  "CadenceEmployeeIdRecognizer": "custom_pattern"}.get(recognizer, "pattern")
        block = next((index for index, start, end in block_spans
                      if start <= item.start and item.end <= end), None)
        return DetectedPII(item.entity_type, page.text[item.start:item.end], item.start,
                           item.end, item.score, method, recognizer, page.page_number, block)

    @staticmethod
    def _block_spans(page):
        # Map only when Engine 2's newline-joined blocks exactly reconstruct text.
        if not page.blocks or "\n".join(block.text for block in page.blocks) != page.text:
            return []
        spans, cursor = [], 0
        for index, block in enumerate(page.blocks):
            spans.append((index, cursor, cursor + len(block.text)))
            cursor += len(block.text) + 1
        return spans

    @staticmethod
    def _build_validation_context(text: str, start: int, end: int, window: int = 200) -> str:
        return text[max(0, start - window):min(len(text), end + window)]
