from uuid import UUID, uuid4

from app.config import get_settings
from app.db.models.attachment import Attachment
from conftest import login_as



def test_catalog_toggle_and_employee_scoping(env, monkeypatch):
    employee = env.users[1]
    headers = login_as(env, employee)
    assert env.client.get("/api/v1/demo/samples", headers=headers).status_code == 404
    monkeypatch.setenv("SHOW_DEMO_SAMPLES", "true")
    get_settings.cache_clear()
    response = env.client.get("/api/v1/demo/samples", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 3
    foreign_headers = login_as(env, env.users[3])
    assert env.client.get(
        "/api/v1/demo/samples", headers=foreign_headers
    ).status_code == 200


def test_file_sample_attachment_is_idempotent_and_employee_owned(env, monkeypatch):
    monkeypatch.setenv("SHOW_DEMO_SAMPLES", "true")
    get_settings.cache_clear()
    headers = login_as(env, env.users[1])
    samples = env.client.get("/api/v1/demo/samples", headers=headers).json()["items"]
    sample = next(item for item in samples if item["kind"] == "file")
    body = {"client_request_id": str(uuid4())}
    first = env.client.post(
        f"/api/v1/demo/samples/{sample['id']}/attachments", json=body, headers=headers
    )
    second = env.client.post(
        f"/api/v1/demo/samples/{sample['id']}/attachments", json=body, headers=headers
    )
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    stored = env.db.get(Attachment, UUID(first.json()["id"]))
    assert stored.employee_id == env.users[1].id
    assert stored.organization_id == env.users[1].organization_id
    unknown = env.client.post(
        f"/api/v1/demo/samples/{uuid4()}/attachments",
        json={"client_request_id": str(uuid4())},
        headers=headers,
    )
    assert unknown.status_code == 404
    message = next(item for item in samples if item["kind"] == "message")
    invalid = env.client.post(
        f"/api/v1/demo/samples/{message['id']}/attachments",
        json={"client_request_id": str(uuid4())},
        headers=headers,
    )
    assert invalid.status_code == 422
