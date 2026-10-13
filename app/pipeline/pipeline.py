"""Synchronous orchestration, without reimplementing any engine logic."""
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from app.engines.file_intelligence import FileIntelligenceEngine
from app.engines.file_intelligence.models import FileMetadata
from app.engines.extraction import ExtractionEngine
from app.engines.extraction.models import ExtractionResult
from app.engines.pii_detection import PIIDetectionEngine
from app.engines.pii_detection.models import PIIDetectionResult
from app.engines.redaction import RedactionEngine
from app.engines.redaction.models import RedactionResult
from app.engines.audit import AuditEngine, AuditResult, ReviewerFeedback
from app.engines.redaction.artifacts import OfficeArtifactEngine, ArtifactResult
from app.engines.redaction.document_artifacts import DocumentArtifactEngine
from .models import PipelineResult, PipelineFailure, ProcessingStatus


class _ClassifiedInput:
    """Reuse Engine 1's result through Engine 2's existing routing contract."""
    def __init__(self, metadata):
        self.metadata = metadata

    def analyze(self, path):
        if Path(path) != self.metadata.path:
            raise ValueError("Extraction source differs from classified source")
        return self.metadata


class _UnsupportedExtraction(ValueError):
    pass


class DocumentPipeline:
    def __init__(self, *, file_intelligence=None, extraction=None, detection=None,
                 redaction=None, audit=None, artifacts=None, artifact_output_dir=None, visual_detection=None):
        self.file_intelligence = file_intelligence
        self.extraction = extraction
        self.detection = detection
        self.redaction = redaction
        self.audit = audit
        self.artifacts = artifacts
        self.artifact_output_dir = artifact_output_dir
        self.visual_detection = visual_detection
        self._default_extraction = extraction is None

    def _engine(self, name, factory):
        engine = getattr(self, name)
        if engine is None:
            engine = factory()
            setattr(self, name, engine)
        return engine

    def set_custom_rules(self, rules):
        from app.engines.pii_detection import PIIDetectionEngine
        det = self._engine("detection", PIIDetectionEngine)
        det.custom_rules = list(rules or [])

    @staticmethod
    def _stage(result, stage, operation, expected_type=None):
        started = perf_counter()
        try:
            value = operation()
            if expected_type is not None and not isinstance(value, expected_type):
                raise TypeError("Unexpected engine result")
            return value
        except Exception as exc:
            code = ("UNSUPPORTED_EXTRACTION" if isinstance(exc, _UnsupportedExtraction)
                    else "SOURCE_NOT_FOUND" if isinstance(exc, FileNotFoundError)
                    else "STAGE_FAILED")
            result.failure = PipelineFailure(stage, code, "Pipeline stage failed; internal review required.")
            result.processing_status = ProcessingStatus.PROCESSING_FAILED
            return None
        finally:
            result.stage_timings[stage] = perf_counter() - started

    def _extract(self, metadata):
        if ((metadata.file_type == "pdf" and metadata.extraction_strategy not in {"text", "ocr", "hybrid"})
                or metadata.file_type not in {"pdf", "docx", "pptx", "image"}):
            raise _UnsupportedExtraction()
        engine = self._engine("extraction", ExtractionEngine)
        if self._default_extraction:
            # Public extract() still selects text/OCR/hybrid; classification is not repeated.
            engine.file_intelligence = _ClassifiedInput(metadata)
        return engine.extract(metadata.path)

    @staticmethod
    def _finish(result, started, prior_runtime=0.0):
        result.total_runtime = prior_runtime + perf_counter() - started
        if result.failure is None:
            result.processing_status = (ProcessingStatus.PROCESSED_REVIEW_REQUIRED
                                        if result.review_queue or (result.artifact_result is not None
                                                                   and not result.artifact_result.artifact_verified)
                                        else ProcessingStatus.PROCESSED_NO_KNOWN_REVIEW)
        return result

    def _office_stages(self, result):
        if result.failure or result.audit_result is None or result.extraction_result.file_type not in {"pdf", "docx", "pptx", "image"}:
            return
        artifact_extraction=deepcopy(result.extraction_result)
        artifact_extraction.visual=result.audit_result.visual_result
        result.artifact_result = self._stage(result, "artifact_redaction", lambda:
            self._engine("artifacts", lambda: DocumentArtifactEngine(self.artifact_output_dir)).redact(
            artifact_extraction, result.audit_result.effective_detection_result, result.redaction_result), ArtifactResult)
        if result.failure:
            return
        result.artifact_result.known_review_complete=result.audit_result.human_review_complete
        result.artifact_result = self._stage(result, "artifact_verification", lambda: self.artifacts.verify(
            artifact_extraction, result.redaction_result, result.artifact_result), ArtifactResult)

    def process(self, file_path: str | Path) -> PipelineResult:
        started = perf_counter()
        result = PipelineResult()

        def classify():
            result.source_path = Path(file_path)
            return self._engine("file_intelligence", FileIntelligenceEngine).analyze(str(result.source_path))

        result.file_intelligence_result = self._stage(result, "file_intelligence", classify, FileMetadata)
        if result.failure:
            return self._finish(result, started)
        result.extraction_result = self._stage(result, "extraction",
            lambda: self._extract(result.file_intelligence_result), ExtractionResult)
        if result.failure:
            return self._finish(result, started)
        from app.engines.visual_detection import VisualInspectionEngine
        from app.engines.visual_detection.models import VisualInspection
        result.extraction_result.visual=self._stage(result,'face_detection',lambda:
            self._engine('visual_detection',VisualInspectionEngine).inspect(result.extraction_result),VisualInspection)
        if result.failure:return self._finish(result,started)
        result.detection_result = self._stage(result, "detection",
            lambda: self._engine("detection", PIIDetectionEngine).detect(result.extraction_result), PIIDetectionResult)
        if result.failure:
            return self._finish(result, started)
        result.redaction_result = self._stage(result, "redaction",
            lambda: self._engine("redaction", RedactionEngine).redact(result.extraction_result, result.detection_result),
            RedactionResult)
        if result.failure:
            return self._finish(result, started)
        result.audit_result = self._stage(result, "audit",
            lambda: self._engine("audit", AuditEngine).create_audit(
                result.extraction_result, result.detection_result, result.redaction_result), AuditResult)
        self._office_stages(result)
        if self._default_extraction and result.extraction_result and result.extraction_result.file_type=='pdf' and not result.failure:
            self._stage(result,'residual_verification',lambda:self._repair_pdf_residuals(result))
        return self._finish(result, started)

    def apply_feedback(self, result: PipelineResult, feedback: ReviewerFeedback) -> PipelineResult:
        started = perf_counter()
        updated = deepcopy(result)
        updated.failure = None
        updated.persisted_path = None  # Changed state has not been saved.
        updated.artifact_result = None

        def apply():
            if result.failure or result.audit_result is None:
                raise ValueError("A successful audit is required")
            return self._engine("audit", AuditEngine).apply_feedback(result.audit_result, feedback)

        updated.audit_result = self._stage(updated, "feedback", apply, AuditResult)
        if updated.audit_result is not None:
            updated.redaction_result = updated.audit_result.redaction_result
            self._office_stages(updated)
        return self._finish(updated, started, result.total_runtime)

    def save_audit(self, result: PipelineResult, *, expected_revision=None) -> PipelineResult:
        started = perf_counter()
        saved = deepcopy(result)
        saved.failure = None
        saved.persisted_path = None

        def save():
            if result.failure or result.audit_result is None:
                raise ValueError("A successful audit is required")
            return self._engine("audit", AuditEngine).save_audit(result.audit_result,
                                                               expected_revision=expected_revision)

        saved.persisted_path = self._stage(saved, "persistence_save", save, Path)
        return self._finish(saved, started, result.total_runtime)

    def load_audit(self, document_id: str) -> PipelineResult:
        started = perf_counter()
        result = PipelineResult()
        result.audit_result = self._stage(result, "persistence_load",
            lambda: self._engine("audit", AuditEngine).load_audit(document_id), AuditResult)
        if result.audit_result is not None:
            audit = result.audit_result
            result.source_path = audit.extraction.source_path
            result.extraction_result = audit.extraction
            result.detection_result = audit.original_detection_result
            result.redaction_result = audit.redaction_result
            self._office_stages(result)
        return self._finish(result, started)

    def _repair_pdf_residuals(self,result):
        """Verify visible known PII, retain original-crop evidence, then regenerate.

        Two repair rounds are bounded. Persistent leaks fail the processing stage;
        manager availability and pending approval never change this engine check.
        """
        from app.engines.extraction.residual import residual_blocks
        extraction=result.extraction_result
        if not any(p.extraction_method=='ocr' for p in extraction.pages):return
        for attempt in range(3):
            pending=residual_blocks(extraction,result.artifact_result,result.redaction_result,self.extraction.ocr_engine)
            if not pending:return
            if attempt==2:raise ValueError('Known sensitive pixels remain after bounded PDF repairs')
            for number,block in pending:
                page=next(p for p in extraction.pages if p.page_number==number)
                page.blocks.append(block)
                page.text='\n'.join(b.text for b in page.blocks)
            result.detection_result=self.detection.detect(extraction)
            result.redaction_result=self.redaction.redact(extraction,result.detection_result)
            result.audit_result=self.audit.create_audit(extraction,result.detection_result,result.redaction_result)
            self._office_stages(result)
            if result.failure:raise ValueError('Residual repair could not regenerate verified artifact')
