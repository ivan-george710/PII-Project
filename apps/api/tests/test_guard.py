from uuid import uuid4

import pytest

from app.services.guard import (
    EventBatch,
    EventRecord,
    LocalEventSink,
    PolicyRule,
    PolicySnapshot,
    RuleEngine,
    StaticPolicyStore,
    sanitize_and_report,
)


def test_enabled_and_disabled_policy_actions_are_reported():
    organization_id, employee_id, conversation_id, submission_id = (uuid4() for _ in range(4))
    policy = PolicySnapshot(
        version="v2",
        rules=[
            PolicyRule(name="email", pattern=r"person@example\.test", enabled=True),
            PolicyRule(name="project", pattern="Northstar", enabled=False),
        ],
    )
    sink = LocalEventSink()
    result = sanitize_and_report(
        organization_id=organization_id,
        employee_id=employee_id,
        conversation_id=conversation_id,
        submission_id=submission_id,
        text="person@example.test Northstar",
        policy_store=StaticPolicyStore(policy),
        engine=RuleEngine(),
        event_sink=sink,
    )
    assert result.sanitized_text == "[REDACTED] Northstar"
    assert {event.action for event in sink.events.values()} == {
        "redact",
        "allowed_disabled",
    }


def test_reporting_failure_propagates_before_provider():
    class FailingSink:
        def record(self, batch: EventBatch) -> None:
            raise RuntimeError("private reporting failure")

    with pytest.raises(RuntimeError):
        sanitize_and_report(
            organization_id=uuid4(),
            employee_id=uuid4(),
            conversation_id=uuid4(),
            submission_id=uuid4(),
            text="plain",
            policy_store=StaticPolicyStore(),
            engine=RuleEngine(),
            event_sink=FailingSink(),
        )
