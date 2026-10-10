from __future__ import annotations

from collections.abc import Iterable
from copy import copy
from pathlib import Path
from typing import Protocol
from uuid import UUID

from pii_guard.detection.validation import (
    DetectionBatch, DetectionConfig, RecognizerCandidate, validate_candidates,
)
from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.models import ExtractedTextBlock, SourceLocation
from pii_guard.rules.builtins import TEXT_RULE_IDS


class TextDetectionBackend(Protocol):
    supported_rule_ids: frozenset[str]

    def recognize(self, text: str) -> list[RecognizerCandidate]: ...


class PresidioBackend:
    """Use AnalyzerEngine's NLP/registry without its containment pruning."""

    def __init__(self, config: DetectionConfig) -> None:
        try:
            import spacy
            from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
            from presidio_analyzer.nlp_engine import SpacyNlpEngine
            from pii_guard.detection.recognizers.employee_id import EmployeeIdRecognizer

            # Presidio's default loader downloads missing models. Processing must
            # instead fail explicitly; model installation is an operator step.
            if not spacy.util.is_package(config.spacy_model) and not Path(config.spacy_model).is_dir():
                raise ValueError("Required NLP model is unavailable")
            nlp = SpacyNlpEngine(models=[{"lang_code": "en", "model_name": config.spacy_model}])
            nlp.load()
            if "ner" not in nlp.nlp["en"].pipe_names:
                raise ValueError("Required named entity recognition is unavailable")
            registry = RecognizerRegistry(supported_languages=["en"])
            registry.load_predefined_recognizers(languages=["en"], nlp_engine=nlp)
            registry.add_recognizer(EmployeeIdRecognizer())
            self.analyzer = AnalyzerEngine(nlp_engine=nlp, registry=registry,
                                          supported_languages=["en"], log_decision_process=False)
            self.recognizers = registry.get_recognizers(language="en", entities=sorted(TEXT_RULE_IDS))
            self.supported_rule_ids = frozenset(entity for rec in self.recognizers for entity in rec.supported_entities) & TEXT_RULE_IDS
            if self.supported_rule_ids != TEXT_RULE_IDS:
                raise ValueError("Required text recognizers are unavailable")
            for recognizer in self.recognizers:
                if not recognizer.is_loaded:
                    recognizer.load()
                    recognizer.is_loaded = True
        except Exception as exc:
            raise ProcessingError(ProcessingErrorCode.EXTRACTION_FAILED,
                                  "Required text detection components or model are unavailable.") from exc

    def recognize(self, text: str) -> list[RecognizerCandidate]:
        artifacts = self.analyzer.nlp_engine.process_text(text, "en")
        results = []
        for recognizer in self.recognizers:
            # PatternRecognizer also prunes containment across its patterns.
            # Analyze each pattern independently; defer deduplication to validation.
            runs = [recognizer]
            if getattr(recognizer, "patterns", None):
                runs = []
                for pattern in recognizer.patterns:
                    run = copy(recognizer)
                    run.patterns = [pattern]
                    runs.append(run)
            for run in runs:
                matches = run.analyze(text=text, entities=sorted(TEXT_RULE_IDS), nlp_artifacts=artifacts)
                for match in matches:
                    if match.entity_type in TEXT_RULE_IDS:
                        results.append(RecognizerCandidate.model_validate({
                            "rule_id": match.entity_type, "start": match.start, "end": match.end,
                            "score": match.score, "recognizer": recognizer.name,
                        }))
        return results


class TextDetector:
    """Detect all text rules independently of policy; returns processing candidates."""

    def __init__(self, config: DetectionConfig | None = None, *,
                 backend: TextDetectionBackend | None = None,
                 submission_id: UUID | None = None) -> None:
        self.config = DetectionConfig.model_validate((config or DetectionConfig()).model_dump())
        self.submission_id = submission_id
        try:
            self.backend = backend if backend is not None else PresidioBackend(self.config)
            if self.backend.supported_rule_ids != TEXT_RULE_IDS:
                raise ValueError("Required text rules are unavailable")
        except Exception as exc:
            raise ProcessingError(ProcessingErrorCode.EXTRACTION_FAILED,
                "Required text detection components or model are unavailable.", submission_id=submission_id) from exc

    def detect(self, *, text: str = "", blocks: Iterable[ExtractedTextBlock] = ()) -> DetectionBatch:
        accepted, rejected = [], []
        if text:
            result = self.detect_message(text)
            accepted.extend(result.accepted)
            rejected.extend(result.rejected)
        for block in blocks:
            result = self.detect_block(block)
            accepted.extend(result.accepted)
            rejected.extend(result.rejected)
        # References, not matched text, identify duplicates across repeated inputs.
        unique = {}
        for candidate in accepted:
            key = (candidate.rule_id, candidate.location.model_dump_json())
            previous = unique.get(key)
            if previous is None or candidate.confidence > previous.confidence:
                unique[key] = candidate
        return DetectionBatch(tuple(unique.values()), tuple(rejected))

    def detect_message(self, text: str) -> DetectionBatch:
        if not text:
            return DetectionBatch()
        location = SourceLocation(artifact_id=None, kind="message", page_number=None,
            slide_number=None, source_ref=None, start=0, end=len(text), bbox=None)
        return self._detect_unit(text, location)

    def detect_block(self, block: ExtractedTextBlock) -> DetectionBatch:
        try:
            validated = ExtractedTextBlock.model_validate(block.model_dump())
        except Exception as exc:
            raise ProcessingError(ProcessingErrorCode.EXTRACTION_FAILED, "Invalid text extraction source.",
                submission_id=self.submission_id, artifact_id=block.location.artifact_id) from exc
        return self._detect_unit(validated.text, validated.location)

    def _detect_unit(self, text: str, location: SourceLocation) -> DetectionBatch:
        try:
            raw = [RecognizerCandidate.model_validate(candidate.model_dump())
                   for candidate in self.backend.recognize(text)]
            return validate_candidates(text, location, raw, self.config)
        except Exception as exc:
            raise ProcessingError(ProcessingErrorCode.EXTRACTION_FAILED,
                "Required text detection failed.", submission_id=self.submission_id,
                artifact_id=location.artifact_id) from exc
