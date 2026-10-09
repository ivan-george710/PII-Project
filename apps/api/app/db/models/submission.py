from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdentityMixin


class Submission(IdentityMixin, Base):
    __tablename__ = "submissions"
    __table_args__ = (
        CheckConstraint("state IN ('processing','completed','failed','cancelled')"),
        UniqueConstraint(
            "employee_id", "conversation_id", "client_request_id",
            name="uq_submission_employee_conversation_request",
        ),
        ForeignKeyConstraint(
            ["employee_id", "organization_id"],
            ["users.id", "users.organization_id"],
            ondelete="CASCADE",
        ),
        Index(
            "uq_submissions_active_conversation",
            "organization_id",
            "conversation_id",
            unique=True,
            sqlite_where=text("state = 'processing'"),
            postgresql_where=text("state = 'processing'"),
        ),
        ForeignKeyConstraint(
            ["conversation_id", "employee_id", "organization_id"],
            [
                "conversations.id",
                "conversations.employee_id",
                "conversations.organization_id",
            ],
            name="fk_submission_conversation_owner",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["assistant_message_id", "conversation_id", "organization_id"],
            [
                "messages.id",
                "messages.conversation_id",
                "messages.organization_id",
            ],
            name="fk_submission_assistant_message",
        ),
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    employee_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    conversation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    client_request_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="processing")
    assistant_message_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    stream_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_sequence: Mapped[int] = mapped_column(nullable=False, default=1)
