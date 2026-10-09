from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.attachment import Attachment
from app.storage.files import LocalFileStorage


def cleanup_expired(
    db: Session, storage: LocalFileStorage, retention_days: int
) -> int:
    if retention_days < 1:
        raise ValueError("Retention must be positive")
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    items = list(
        db.scalars(
            select(Attachment).where(Attachment.created_at < cutoff)
        )
    )
    for item in items:
        storage.delete(item.original_key)
        if item.sanitized_key:
            storage.delete(item.sanitized_key)
        db.delete(item)
    db.commit()
    return len(items)
