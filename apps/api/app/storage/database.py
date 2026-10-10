"""Minimal durable private storage for this deployment's signed API uploads.

Routes authorize ownership before reading keys. No public URLs to original bytes.
Production signing uses the shared session secret, surviving cold starts.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from app.db.models.file_blob import FileBlob
from app.db.models.attachment import Attachment
from app.schemas.common import ApiError
from app.storage.files import LocalFileStorage, MAX_BYTES


class DatabaseFileStorage(LocalFileStorage):
    def __init__(self, factory, secret):
        super().__init__(secret=secret)
        self.factory = factory

    def _put(self, key, content):
        if not 0 < len(content) <= MAX_BYTES:
            raise ApiError(413, "FILE_TOO_LARGE", "File exceeds the supported size")
        kind, organization, employee, aid = key.split("/")
        aid = UUID(aid)
        with self.factory() as db:
            attachment = db.get(Attachment, aid)
            if (
                kind not in {"original", "sanitized"}
                or attachment is None
                or attachment.organization_id != UUID(organization)
                or attachment.employee_id != UUID(employee)
            ):
                raise ApiError(404, "NOT_FOUND", "File unavailable")
            row = db.get(FileBlob, key)
            if row is None:
                db.add(FileBlob(key=key, attachment_id=aid, content=content))
            else:
                row.content = content
            db.commit()

    def receive_upload(self, organization_id, employee_id, attachment_id, content):
        self._put(
            self._key("original", organization_id, employee_id, attachment_id), content
        )

    def write_sanitized(self, organization_id, employee_id, attachment_id, content):
        key = self._key("sanitized", organization_id, employee_id, attachment_id)
        self._put(key, content)
        return key

    def read_original(self, key):
        with self.factory() as db:
            row = db.get(FileBlob, key)
            if row is None:
                raise FileNotFoundError("Private file unavailable")
            return row.content

    read_sanitized = read_original

    def delete(self, key):
        with self.factory() as db:
            row = db.get(FileBlob, key)
            if row is not None:
                db.delete(row)
                db.commit()

    def verify_upload(
        self,
        organization_id,
        employee_id,
        attachment_id,
        filename,
        mime_type,
        expected_size,
    ):
        content = self.read_original(
            self._key("original", organization_id, employee_id, attachment_id)
        )
        with TemporaryDirectory(prefix="pii-upload-verify-") as root:
            verifier = LocalFileStorage(root)
            verifier.receive_upload(
                organization_id, employee_id, attachment_id, content
            )
            return verifier.verify_upload(
                organization_id,
                employee_id,
                attachment_id,
                filename,
                mime_type,
                expected_size,
            )
