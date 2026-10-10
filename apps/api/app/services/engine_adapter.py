"""Connect chat's guard contract with the engine and durable company services."""

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from app.services.guard import PolicySnapshot, SanitizeResult, Finding
from app.schemas.reports import Finding as DetailedFinding, EventBatch as ReportBatch
from app.services import rules, reporting


@lru_cache(maxsize=1)
def privacy_engine():
    from pii_guard.pipeline import PrivacyEngine

    return PrivacyEngine()


class DatabasePolicyStore:
    def __init__(self, db):
        self.db = db

    def get_snapshot(self, organization_id):
        snapshot = rules.get_snapshot(self.db, organization_id)
        return PolicySnapshot(
            version=str(snapshot.version),
            engine_policy=snapshot.model_dump(mode="json"),
        )


class PipelineAdapter:
    def __init__(self, engine=None):
        self.engine = engine

    def sanitize(self, request):
        from pii_guard.models import (
            SanitizeRequest,
            ArtifactInput,
            PolicySnapshot as EnginePolicy,
        )

        if request.policy.engine_policy is None:
            raise ValueError("Complete company policy required")
        policy = EnginePolicy.model_validate(request.policy.engine_policy)
        if (
            policy.organization_id != request.organization_id
            or str(policy.version) != request.policy.version
        ):
            raise ValueError("Policy identity mismatch")
        # Chat also sanitizes empty history/current text when only files are sent.
        if not request.text.strip() and request.original_bytes is None:
            return SanitizeResult(sanitized_text=request.text)
        with TemporaryDirectory(prefix="pii-guard-api-") as directory:
            root = Path(directory)
            artifacts = []
            if request.original_bytes is not None:
                path = root / "source"
                path.write_bytes(request.original_bytes)
                path.chmod(0o600)
                artifacts = [
                    ArtifactInput(
                        id=request.artifact_id or uuid4(),
                        filename=request.filename,
                        source_path=path,
                        declared_mime=request.mime_type,
                    )
                ]
            engine = self.engine or privacy_engine()
            result = engine.sanitize(
                SanitizeRequest(
                    submission_id=uuid4(),
                    text=request.text,
                    artifacts=artifacts,
                    policy=policy,
                    output_dir=root / "output",
                )
            )
            data = (
                result.artifacts[0].output_path.read_bytes()
                if result.artifacts
                else None
            )
            text = (
                result._artifact_texts[artifacts[0].id]
                if artifacts
                else result.sanitized_text
            )
            return SanitizeResult(
                sanitized_text=text,
                sanitized_bytes=data,
                findings=[
                    Finding(
                        rule=f.rule_id,
                        action="redact" if f.action == "redacted" else f.action,
                        count=1,
                        details=[DetailedFinding.model_validate(f.model_dump())],
                    )
                    for f in result.findings
                ],
            )


class DatabaseEventSink:
    def __init__(self, db, submission, employee_id):
        self.db = db
        self.submission = submission
        self.employee_id = employee_id
        self.policy_version = None

    def record(self, batch):
        details = []
        for event in batch.events:
            if (
                event.organization_id != self.submission.organization_id
                or event.employee_id != self.employee_id
            ):
                raise ValueError("Reporting identity mismatch")
            details.extend(event.details)
        # The schema contains locations/categories only, never matched content,
        # original filenames, passwords or image bytes.
        reporting.record(
            self.db,
            ReportBatch(
                submission_id=self.submission.id,
                organization_id=self.submission.organization_id,
                employee_id=self.employee_id,
                policy_version=int(self.policy_version),
                occurred_at=datetime.now(timezone.utc),
                status="completed",
                findings=details,
            ),
        )

    def record_failure(self):
        if self.policy_version is None:
            return
        from app.db.models.pii_event import PiiEvent

        event = (
            self.db.query(PiiEvent)
            .filter(
                PiiEvent.company_id == self.submission.organization_id,
                PiiEvent.submission_id == self.submission.id,
            )
            .first()
        )
        if event is not None:
            event.status = "failed"
            event.failure_code = "PROCESSING_FAILED"
            self.db.commit()
        else:
            reporting.record(
                self.db,
                ReportBatch(
                    submission_id=self.submission.id,
                    organization_id=self.submission.organization_id,
                    employee_id=self.employee_id,
                    policy_version=int(self.policy_version),
                    occurred_at=datetime.now(timezone.utc),
                    status="failed",
                    failure_code="PROCESSING_FAILED",
                    findings=[],
                ),
            )
