from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdentityMixin


class Attachment(IdentityMixin, Base):
    __tablename__ = "attachments"
    __table_args__ = (
        Index("ix_attachments_owner", "organization_id", "employee_id", "id"),
        CheckConstraint("size_bytes BETWEEN 1 AND 26214400"),
        CheckConstraint("state IN ('pending_upload','uploaded','processing','sanitized','failed')"),
        UniqueConstraint(
            "employee_id",
            "sample_id",
            "sample_request_id",
            name="uq_attachment_employee_sample_request",
        ),
        ForeignKeyConstraint(
            ["employee_id", "organization_id"],
            ["users.id", "users.organization_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["conversation_id", "employee_id", "organization_id"],
            [
                "conversations.id",
                "conversations.employee_id",
                "conversations.organization_id",
            ],
            name="fk_attachment_conversation_owner",
            ondelete="CASCADE",
        ),
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    employee_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    conversation_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    original_key: Mapped[str] = mapped_column(String(512), nullable=False)
    sanitized_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sample_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    sample_request_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_upload")
