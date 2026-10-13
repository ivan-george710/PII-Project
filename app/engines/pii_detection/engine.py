"""Page-local Presidio detection with exactly one disposition per candidate."""
from math import isfinite
from pathlib import Path
import re
import regex as bounded_regex

from presidio_analyzer import AnalyzerEngine

from app.engines.extraction.models import ExtractionResult
from .models import DetectedPII, PIIDetectionResult, DetectionProcessingError
from .recognizers import EmployeeIdRecognizer, SensitiveFieldRecognizer, IntroductionRecognizer, MailboxRecognizer, LabeledPIIRecognizer
from .validation import ValidationDecision, validate_detection


class PIIDetectionEngine:
    def __init__(self, *, analyzer=None, custom_rules=None) -> None:
        """Injected analyzers are already configured; default analyzer registers IDs once."""
        if analyzer is None:
            try:
                analyzer = AnalyzerEngine()
                analyzer.registry.add_recognizer(EmployeeIdRecognizer())
                analyzer.registry.add_recognizer(SensitiveFieldRecognizer())
                analyzer.registry.add_recognizer(MailboxRecognizer())
                analyzer.registry.add_recognizer(LabeledPIIRecognizer())
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
                if hasattr(self.analyzer, "nlp_engine"):
                    raw.extend(IntroductionRecognizer.candidates(page.text, self.analyzer))
                    seen = {(d.entity_type,d.start,d.end) for d in raw}
                    raw.extend(d for d in self._normalized_nlp_candidates(page.text)
                               if (d.entity_type,d.start,d.end) not in seen)
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
                    matcher = bounded_regex.compile(pattern if is_regex else re.escape(pattern), bounded_regex.IGNORECASE)
                    for m in matcher.finditer(page.text,timeout=.05):
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
                    raise DetectionProcessingError("A manager rule is invalid or exceeded its processing limit") from None
            output.pages_analyzed.append(page.page_number)
            output.raw_candidate_count += len(candidates)
            # Keep duplicate raw candidates; no overlap removal in Engine 3.
            candidates.sort(key=lambda d: (d.start, d.end, d.entity_type))
            for detection in candidates:
                context = self._build_validation_context(page.text, detection.start, detection.end)
                if page.extraction_method=='pptx' and detection.recognizer=='SpacyRecognizer' and detection.entity_type=='PERSON' and '\n' in detection.text:
                    detection.validation_decision='REJECT';detection.final_decision='REJECT'
                    detection.validation_reason='multi_shape_person_context'
                    output.rejected.append(detection)
                    continue
                intro = next((d for d in candidates if d.recognizer == 'IntroductionRecognizer'
                              and detection.start <= d.start and d.end <= detection.end), None)
                if intro and detection.recognizer != 'IntroductionRecognizer' and detection.start < intro.start:
                    detection.validation_decision='REJECT'
                    detection.validation_reason='introduction_context_not_name'
                    detection.final_decision='REJECT'
                    output.rejected.append(detection)
                    continue
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
        for page in extraction_result.pages:
            cursor=0
            for index,block in enumerate(page.blocks or []):
                if block.mask_only and block.text:
                    output.detections.append(DetectedPII('PII_REGION',block.text,cursor,cursor+len(block.text),1.0,
                        'residual_ocr','ResidualPrivacyRecognizer',page.page_number,index,
                        validation_decision='CONFIRM',validation_reason='known_sensitive_pixels_in_serialized_output',final_decision='CONFIRM'))
                    output.raw_candidate_count+=1
                cursor+=len(block.text)+1
        self._protect_known_values_and_overlaps(extraction_result, output)
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

    @staticmethod
    def _protect_known_values_and_overlaps(extraction, output):
        """Protect repeated confirmed values and crossing sensitive spans.

        Original classifier dispositions remain in the audit. Additional exact
        or union candidates supply complete removal geometry, not new guesses.
        """
        from .models import DetectedPII
        known = {d.text: d for d in output.detections + output.review}
        existing = {(d.page_number,d.start,d.end) for d in output.detections + output.review + output.rejected}
        for page in extraction.pages:
            for value,original in known.items():
                for match in re.finditer((r"(?<!\w)" + re.escape(value) + r"(?!\w)") if len(value)<4 else re.escape(value),page.text):
                    key=(page.page_number,match.start(),match.end())
                    if key in existing:
                        continue
                    d=DetectedPII(original.entity_type,match.group(),match.start(),match.end(),
                        original.confidence,'known_value','RepeatedConfirmedValue',page.page_number,
                        validation_decision='CONFIRM',validation_reason='exact_confirmed_value_repeat',final_decision='CONFIRM')
                    output.detections.append(d);output.raw_candidate_count+=1;existing.add(key)
            candidates=sorted((d for d in output.detections+output.review if d.page_number==page.page_number),key=lambda d:d.start)
            groups=[]
            for d in candidates:
                if not groups or d.start>=max(e.end for e in groups[-1]):groups.append([d])
                else:groups[-1].append(d)
            for group in groups:
                start,end=min(d.start for d in group),max(d.end for d in group)
                if any(d.start==start and d.end==end for d in group):continue
                output.detections.append(DetectedPII('PII_SPAN',page.text[start:end],start,end,1.0,
                    'privacy_union','SensitiveSpanUnion',page.page_number,
                    validation_decision='CONFIRM',validation_reason='crossing_pii_span_union',final_decision='CONFIRM'))
                output.raw_candidate_count+=1

    def _normalized_nlp_candidates(self, text):
        """Run the same classifier with OCR word spacing, mapping back exactly."""
        from presidio_analyzer import RecognizerResult
        chars, offsets = [], []
        for index,char in enumerate(text):
            if index and ((text[index-1].islower() and char.isupper())
                          or (text[index-1] == '.' and char.isupper())):
                chars.append(' ');offsets.append(index)
            chars.append(char);offsets.append(index)
        normalized=''.join(chars)
        if normalized==text:return []
        result=[]
        for candidate in self.analyzer.analyze(text=normalized, language='en'):
            name=(candidate.recognition_metadata or {}).get('recognizer_name')
            if name!='SpacyRecognizer' or candidate.entity_type not in {'PERSON','LOCATION','NRP'}:
                continue
            start,end=offsets[candidate.start],offsets[candidate.end-1]+1
            if start>=end:continue
            result.append(RecognizerResult(candidate.entity_type,start,end,candidate.score,
                recognition_metadata=candidate.recognition_metadata))
        return result
