from uuid import uuid4
from urllib.parse import urlsplit

from app.db.models.attachment import Attachment
from app.main import app
from app.routes.uploads import router as uploads_router
from app.storage.files import LocalFileStorage
from conftest import login_as

app.include_router(uploads_router)


def test_upload_status_is_scoped_to_employee(env, tmp_path):
    employee, foreign = env.users[1], env.users[3]
    storage = LocalFileStorage(tmp_path, b"test-storage-signing-secret")
    attachment = Attachment(
        organization_id=employee.organization_id,
        employee_id=employee.id,
        original_key="original/test",
        sanitized_key=None,
        filename="test.pdf",
        mime_type="application/pdf",
        size_bytes=8,
        state="pending_upload",
    )
    env.db.add(attachment)
    env.db.commit()
    headers = login_as(env, employee)
    assert env.client.get(
        f"/api/v1/uploads/{attachment.id}", headers=headers
    ).status_code == 200
    foreign_headers = login_as(env, foreign)
    assert env.client.get(
        f"/api/v1/uploads/{attachment.id}", headers=foreign_headers
    ).status_code == 404


def test_storage_rejects_size_and_invalid_pdf(tmp_path):
    storage = LocalFileStorage(tmp_path)
    organization_id, employee_id, attachment_id = (uuid4() for _ in range(3))
    storage.receive_upload(organization_id, employee_id, attachment_id, b"not a pdf")
    try:
        storage.verify_upload(
            organization_id,
            employee_id,
            attachment_id,
            "test.pdf",
            "application/pdf",
            9,
        )
        assert False, "Invalid signature should be rejected"
    except Exception as error:
        assert getattr(error, "status", None) == 415


def test_signed_upload_is_validated_before_available(env):
    headers = login_as(env, env.users[1])
    content = b"%PDF-1.4"
    initialized = env.client.post(
        "/api/v1/uploads/init",
        json={
            "filename": "fixture.pdf",
            "declared_mime": "application/pdf",
            "size_bytes": len(content),
        },
        headers=headers,
    )
    assert initialized.status_code == 201
    grant = initialized.json()["upload"]
    location = urlsplit(grant["url"])
    put = env.client.put(
        location.path + "?" + location.query,
        content=content,
        headers=grant["headers"],
    )
    assert put.status_code == 204
    completed = env.client.post(
        f"/api/v1/uploads/{initialized.json()['attachment']['id']}/complete",
        json={},
        headers=headers,
    )
    assert completed.status_code == 200
    assert completed.json()["state"] == "uploaded"
