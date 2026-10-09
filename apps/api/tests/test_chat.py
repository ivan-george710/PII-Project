import json
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.db.models.conversation import Conversation
from app.db.models.attachment import Attachment
from app.db.models.submission import Submission
from app.llm.client import ProviderDelta
from app.services.guard import (
    EventBatch,
    LocalEventSink,
    PolicyRule,
    PolicySnapshot,
    RuleEngine,
    StaticPolicyStore,
)
from conftest import login_as



def test_conversations_are_employee_scoped(env):
    employee = env.users[1]
    foreign_employee = env.users[3]
    headers = login_as(env, employee)
    created = env.client.post(
        "/api/v1/conversations", json={"title": " Private chat "}, headers=headers
    )
    assert created.status_code == 201
    conversation_id = created.json()["id"]
    assert created.json()["title"] == "Private chat"
    assert env.client.get(
        f"/api/v1/conversations/{conversation_id}/messages", headers=headers
    ).status_code == 200

    foreign_conversation = Conversation(
        organization_id=foreign_employee.organization_id,
        employee_id=foreign_employee.id,
        title="Foreign",
    )
    env.db.add(foreign_conversation)
    env.db.commit()
    assert env.client.get(
        f"/api/v1/conversations/{foreign_conversation.id}/messages", headers=headers
    ).status_code == 404


def test_submission_stream_sanitizes_and_replays_without_provider_call(env):
    class Provider:
        def __init__(self):
            self.requests = []

        async def stream(self, request):
            self.requests.append(request)
            yield ProviderDelta(text="safe ")
            yield ProviderDelta(text="reply")

    provider = Provider()
    env.client.app.state.policy_store = StaticPolicyStore()
    env.client.app.state.sanitization_engine = RuleEngine()
    env.client.app.state.event_sink = LocalEventSink()
    env.client.app.state.llm_client = provider
    headers = login_as(env, env.users[1])
    conversation = env.client.post(
        "/api/v1/conversations", json={"title": "Test"}, headers=headers
    ).json()
    request = {
        "text": "My email is dana@example.test",
        "attachment_ids": [],
        "client_request_id": str(uuid4()),
    }
    response = env.client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json=request,
        headers=headers,
    )
    assert response.status_code == 200
    assert "event: sanitized" in response.text
    assert "event: delta" in response.text
    assert "event: done" in response.text
    assert "dana@example.test" not in json.dumps(
        [message.sanitized_text for message in provider.requests[0].messages]
    )
    assert provider.requests[0].messages[-1].sanitized_text.endswith("[REDACTED]")
    replay = env.client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json=request,
        headers=headers,
    )
    assert replay.status_code == 200
    assert replay.text == response.text
    assert len(provider.requests) == 1


def test_duplicate_request_id_with_different_body_conflicts(env):
    for attribute in ("policy_store", "sanitization_engine", "event_sink", "llm_client"):
        if hasattr(env.client.app.state, attribute):
            delattr(env.client.app.state, attribute)
    headers = login_as(env, env.users[1])
    conversation = env.client.post(
        "/api/v1/conversations", json={"title": "Test"}, headers=headers
    ).json()
    request_id = str(uuid4())
    body = {
        "text": "first",
        "attachment_ids": [],
        "client_request_id": request_id,
    }
    response = env.client.post(
        f"/api/v1/conversations/{conversation['id']}/messages", json=body, headers=headers
    )
    assert response.status_code == 503
    body["text"] = "different"
    conflict = env.client.post(
        f"/api/v1/conversations/{conversation['id']}/messages", json=body, headers=headers
    )
    assert conflict.status_code == 409


def test_policy_change_resanitizes_retained_history(env):
    class Provider:
        def __init__(self):
            self.requests = []

        async def stream(self, request):
            self.requests.append(request)
            yield ProviderDelta(text="ok")

    provider = Provider()
    env.client.app.state.policy_store = StaticPolicyStore()
    env.client.app.state.sanitization_engine = RuleEngine()
    env.client.app.state.event_sink = LocalEventSink()
    env.client.app.state.llm_client = provider
    headers = login_as(env, env.users[1])
    conversation = env.client.post(
        "/api/v1/conversations", json={}, headers=headers
    ).json()
    first = {
        "text": "Project Northstar is fictional.",
        "attachment_ids": [],
        "client_request_id": str(uuid4()),
    }
    env.client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json=first,
        headers=headers,
    )
    env.client.app.state.policy_store = StaticPolicyStore(
        PolicySnapshot(
            version="v2",
            rules=[
                PolicyRule(
                    name="project",
                    pattern="Northstar",
                    enabled=True,
                )
            ],
        )
    )
    second = {
        "text": "Please summarize this.",
        "attachment_ids": [],
        "client_request_id": str(uuid4()),
    }
    env.client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json=second,
        headers=headers,
    )
    retained = provider.requests[-1].messages[0].sanitized_text
    assert "Northstar" not in retained
    assert "[REDACTED]" in retained


def test_reporting_failure_blocks_provider_and_emits_no_done(env):
    class FailingSink:
        def record(self, batch: EventBatch) -> None:
            raise RuntimeError("reporting details must not leak")

    class Provider:
        def __init__(self):
            self.called = False

        async def stream(self, request):
            self.called = True
            yield ProviderDelta(text="should never happen")

    provider = Provider()
    env.client.app.state.policy_store = StaticPolicyStore()
    env.client.app.state.sanitization_engine = RuleEngine()
    env.client.app.state.event_sink = FailingSink()
    env.client.app.state.llm_client = provider
    headers = login_as(env, env.users[1])
    conversation = env.client.post(
        "/api/v1/conversations", json={}, headers=headers
    ).json()
    response = env.client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={
            "text": "No sensitive text.",
            "attachment_ids": [],
            "client_request_id": str(uuid4()),
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert "event: error" in response.text
    assert "event: done" not in response.text
    assert "reporting details" not in response.text
    assert provider.called is False


def test_one_persisted_active_submission_per_conversation(env):
    headers = login_as(env, env.users[1])
    conversation = env.client.post(
        "/api/v1/conversations", json={}, headers=headers
    ).json()
    env.db.add(
        Submission(
            organization_id=env.users[1].organization_id,
            employee_id=env.users[1].id,
            conversation_id=UUID(conversation["id"]),
            client_request_id=uuid4(),
            request_hash="0" * 64,
            state="processing",
        )
    )
    env.db.commit()
    response = env.client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={
            "text": "hello",
            "attachment_ids": [],
            "client_request_id": str(uuid4()),
        },
        headers=headers,
    )
    assert response.status_code == 409


def test_storage_failure_and_invalid_provider_delta_block_done(env):
    class Provider:
        def __init__(self):
            self.called = False

        async def stream(self, request):
            self.called = True
            yield {"sensitive raw": "provider data"}

    provider = Provider()
    env.client.app.state.policy_store = StaticPolicyStore()
    env.client.app.state.sanitization_engine = RuleEngine()
    env.client.app.state.event_sink = LocalEventSink()
    env.client.app.state.llm_client = provider
    headers = login_as(env, env.users[1])
    conversation = env.client.post(
        "/api/v1/conversations", json={}, headers=headers
    ).json()
    missing_file = Attachment(
        organization_id=env.users[1].organization_id,
        employee_id=env.users[1].id,
        conversation_id=None,
        original_key="original/nonexistent",
        sanitized_key=None,
        filename="missing.pdf",
        mime_type="application/pdf",
        size_bytes=8,
        state="uploaded",
    )
    env.db.add(missing_file)
    env.db.commit()
    failed_storage = env.client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={
            "text": "",
            "attachment_ids": [str(missing_file.id)],
            "client_request_id": str(uuid4()),
        },
        headers=headers,
    )
    assert "event: error" in failed_storage.text
    assert "event: done" not in failed_storage.text
    assert not provider.called

    invalid_delta = env.client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={
            "text": "safe content",
            "attachment_ids": [],
            "client_request_id": str(uuid4()),
        },
        headers=headers,
    )
    assert "event: error" in invalid_delta.text
    assert "event: done" not in invalid_delta.text
    assert provider.called
