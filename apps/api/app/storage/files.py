import hashlib
import hmac
import os
import shutil
import tempfile
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from app.schemas.common import ApiError
from app.schemas.uploads import AllowedMime, UploadGrant

MAX_BYTES = 25 * 1024 * 1024
MIME_EXTENSIONS = {
    "application/pdf": {".pdf"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
        ".docx"
    },
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": {
        ".pptx"
    },
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
}


class LocalFileStorage:
    """Development/local private file store; replace with a signed object-store adapter."""

    def __init__(self, root: str | Path | None = None, secret: bytes | None = None):
        self.root = Path(
            root
            or os.environ.get(
                "PII_STORAGE_DIR",
                str(Path(tempfile.gettempdir()) / "pii-guard-private-uploads"),
            )
        ).resolve()
        self._secret = secret or os.urandom(32)

    def create_upload(
        self,
        organization_id: UUID,
        employee_id: UUID,
        attachment_id: UUID,
        filename: str,
        mime_type: AllowedMime,
        size_bytes: int,
    ) -> UploadGrant:
        expires = datetime.now(UTC) + timedelta(minutes=10)
        token = self._signature(organization_id, employee_id, attachment_id, expires)
        from app.config import get_settings

        url = (
            get_settings().public_app_url.rstrip("/")
            + f"/api/v1/uploads/{attachment_id}/content"
            + f"?expires={int(expires.timestamp())}&signature={token}"
        )
        return UploadGrant(
            url=url,
            headers={"Content-Type": mime_type},
            expires_at=expires,
        )

    def verify_signature(
        self,
        organization_id: UUID,
        employee_id: UUID,
        attachment_id: UUID,
        expires: int,
        signature: str,
    ) -> bool:
        now = int(datetime.now(UTC).timestamp())
        if expires < now or expires > now + 600:
            return False
        expected = self._signature(
            organization_id,
            employee_id,
            attachment_id,
            datetime.fromtimestamp(expires, UTC),
        )
        return hmac.compare_digest(expected, signature)

    def verify_upload(
        self,
        organization_id: UUID,
        employee_id: UUID,
        attachment_id: UUID,
        filename: str,
        mime_type: AllowedMime,
        expected_size: int,
    ) -> tuple[str, int, str]:
        key = self._key("original", organization_id, employee_id, attachment_id)
        path = self._path(key)
        if not path.is_file():
            raise ApiError(422, "UPLOAD_MISSING", "Uploaded file is unavailable")
        size = path.stat().st_size
        if size != expected_size:
            raise ApiError(422, "SIZE_MISMATCH", "Uploaded file size does not match")
        if (
            not 0 < size <= MAX_BYTES
            or Path(filename).suffix.lower() not in MIME_EXTENSIONS[mime_type]
            or not self._content_matches(path, mime_type)
        ):
            raise ApiError(415, "UNSUPPORTED_FILE", "File format is not supported")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return key, size, digest

    def receive_upload(
        self,
        organization_id: UUID,
        employee_id: UUID,
        attachment_id: UUID,
        content: bytes,
    ) -> None:
        if not content or len(content) > MAX_BYTES:
            raise ApiError(413, "FILE_TOO_LARGE", "File size is outside the allowed limit")
        key = self._key("original", organization_id, employee_id, attachment_id)
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".pending")
        temporary.write_bytes(content)
        temporary.replace(path)

    def read_original(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def write_sanitized(
        self, organization_id: UUID, employee_id: UUID, attachment_id: UUID, content: bytes
    ) -> str:
        key = self._key("sanitized", organization_id, employee_id, attachment_id)
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".pending")
        temporary.write_bytes(content)
        temporary.replace(path)
        return key

    def read_sanitized(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()

    def _key(
        self, kind: str, organization_id: UUID, employee_id: UUID, attachment_id: UUID
    ) -> str:
        return f"{kind}/{organization_id}/{employee_id}/{attachment_id}"

    def _path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if self.root not in candidate.parents:
            raise ApiError(404, "NOT_FOUND", "File unavailable")
        return candidate

    def _signature(
        self,
        organization_id: UUID,
        employee_id: UUID,
        attachment_id: UUID,
        expires: datetime,
    ) -> str:
        value = f"{organization_id}:{employee_id}:{attachment_id}:{int(expires.timestamp())}"
        import hashlib

        return hmac.new(self._secret, value.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _content_matches(path: Path, mime_type: str) -> bool:
        with path.open("rb") as source:
            prefix = source.read(16)
        if mime_type == "application/pdf":
            return prefix.startswith(b"%PDF-")
        if mime_type == "image/png":
            return prefix.startswith(b"\x89PNG\r\n\x1a\n")
        if mime_type == "image/jpeg":
            return prefix.startswith(b"\xff\xd8\xff")
        if mime_type in {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        }:
            if not prefix.startswith(b"PK"):
                return False
            try:
                with zipfile.ZipFile(path) as archive:
                    names = set(archive.namelist())
                    required = (
                        "word/document.xml"
                        if mime_type.endswith("wordprocessingml.document")
                        else "ppt/presentation.xml"
                    )
                    return required in names
            except (OSError, zipfile.BadZipFile):
                return False
        return False


def storage_for_request() -> LocalFileStorage:
    from app.config import get_settings

    settings = get_settings()
    if settings.app_env == "production":
        raise ApiError(503, "STORAGE_UNAVAILABLE", "File storage is unavailable")
    if not hasattr(storage_for_request, "_storage"):
        storage_for_request._storage = LocalFileStorage()  # type: ignore[attr-defined]
    return storage_for_request._storage  # type: ignore[attr-defined]
