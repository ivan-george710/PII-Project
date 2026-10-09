import re
import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from pydantic import ConfigDict, Field

from app.schemas.common import Schema


class PolicyRule(Schema):
    model_config = ConfigDict(
        extra="forbid", validate_assignment=True, from_attributes=True, frozen=True
    )
    name: str = Field(min_length=1, max_length=80)
    pattern: str = Field(min_length=1, max_length=300)
    enabled: bool
    action: str = "redact"


class PolicySnapshot(Schema):
    model_config = ConfigDict(
        extra="forbid", validate_assignment=True, from_attributes=True, frozen=True
    )
    version: str = Field(min_length=1, max_length=100)
    rules: tuple[PolicyRule, ...] = Field(max_length=100)


class SanitizeRequest(Schema):
    organization_id: UUID
    policy: PolicySnapshot
    text: str = Field(max_length=100_000)
    filename: str | None = None
    mime_type: str | None = None
    original_bytes: bytes | None = None


class Finding(Schema):
    rule: str
    action: str
    count: int = Field(strict=True, ge=1)


class SanitizeResult(Schema):
    sanitized_text: str
    sanitized_bytes: bytes | None = None
    findings: list[Finding] = Field(default_factory=list)


class EventRecord(Schema):
    event_key: str = Field(min_length=1, max_length=200)
    organization_id: UUID
    employee_id: UUID
    conversation_id: UUID
    attachment_id: UUID | None = None
    rule: str
    action: str
    count: int = Field(strict=True, ge=1)
    policy_version: str


class EventBatch(Schema):
    events: list[EventRecord] = Field(max_length=1000)


class PolicyStore(Protocol):
    def get_snapshot(self, organization_id: UUID) -> PolicySnapshot: ...


class Engine(Protocol):
    def sanitize(self, request: SanitizeRequest) -> SanitizeResult: ...


class EventSink(Protocol):
    def record(self, batch: EventBatch) -> None: ...


@dataclass
class GuardResult:
    policy: PolicySnapshot
    sanitized_text: str
    sanitized_bytes: bytes | None
    findings: list[Finding]


class RuleEngine:
    """Basic deterministic policy engine; production injects the document engine."""

    def sanitize(self, request: SanitizeRequest) -> SanitizeResult:
        text = request.text
        findings: list[Finding] = []
        for rule in request.policy.rules:
            try:
                pattern = re.compile(rule.pattern, re.IGNORECASE)
            except re.error:
                raise ValueError("Policy contains an invalid rule") from None
            matches = list(pattern.finditer(text))
            if not matches:
                continue
            if rule.enabled:
                text = pattern.sub("[REDACTED]", text)
                findings.append(Finding(rule=rule.name, action=rule.action, count=len(matches)))
            else:
                findings.append(
                    Finding(rule=rule.name, action="allowed_disabled", count=len(matches))
                )
        sanitized_bytes = None
        if request.original_bytes is not None:
            try:
                decoded = request.original_bytes.decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError("Document sanitizer is unavailable") from None
            sanitized_text_result = self.sanitize(
                SanitizeRequest(organization_id=request.organization_id, policy=request.policy, text=decoded)
            )
            sanitized_text = sanitized_text_result.sanitized_text
            sanitized_bytes = sanitized_text.encode("utf-8")
            findings.extend(sanitized_text_result.findings)
        return SanitizeResult(
            sanitized_text=text,
            sanitized_bytes=sanitized_bytes,
            findings=findings,
        )


def sanitize_and_report(
    *,
    organization_id: UUID,
    employee_id: UUID,
    conversation_id: UUID,
    text: str,
    policy_store: PolicyStore,
    engine: Engine,
    event_sink: EventSink,
    submission_id: UUID,
    attachment_id: UUID | None = None,
    filename: str | None = None,
    mime_type: str | None = None,
    original_bytes: bytes | None = None,
) -> GuardResult:
    policy = PolicySnapshot.model_validate(
        policy_store.get_snapshot(organization_id).model_dump()
    )
    result = SanitizeResult.model_validate(
        engine.sanitize(
            SanitizeRequest(
                organization_id=organization_id,
                policy=policy,
                text=text,
                filename=filename,
                mime_type=mime_type,
                original_bytes=original_bytes,
            )
        ).model_dump()
    )
    event_sink.record(
        EventBatch(
            events=[
                EventRecord(
                    event_key=f"{submission_id}:{policy.version}:{attachment_id or 'text'}:{index}",
                    organization_id=organization_id,
                    employee_id=employee_id,
                    conversation_id=conversation_id,
                    attachment_id=attachment_id,
                    rule=item.rule,
                    action=item.action,
                    count=item.count,
                    policy_version=policy.version,
                )
                for index, item in enumerate(result.findings)
            ]
        )
    )
    return GuardResult(
        policy=policy,
        sanitized_text=result.sanitized_text,
        sanitized_bytes=result.sanitized_bytes,
        findings=result.findings,
    )


class StaticPolicyStore:
    """Explicit development/test policy; production should inject the policy service."""

    def __init__(self, policy: PolicySnapshot | None = None):
        self.policy = policy or PolicySnapshot(
            version="development-v1",
            rules=[
                PolicyRule(
                    name="email",
                    pattern=r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
                    enabled=True,
                ),
                PolicyRule(
                    name="phone",
                    pattern=r"\b(?:\+?1[- .]?)?\(?\d{3}\)?[- .]?\d{3}[- .]?\d{4}\b",
                    enabled=True,
                ),
                PolicyRule(
                    name="employee_id",
                    pattern=r"\bEMP-\d{4,8}\b",
                    enabled=True,
                ),
            ],
        )

    def get_snapshot(self, organization_id: UUID) -> PolicySnapshot:
        return PolicySnapshot.model_validate(self.policy.model_dump())


class LocalEventSink:
    """Development-only event sink. Inject durable reporting in production."""

    def __init__(self):
        self.events: dict[str, EventRecord] = {}

    def record(self, batch: EventBatch) -> None:
        for event in batch.events:
            self.events.setdefault(event.event_key, event)
