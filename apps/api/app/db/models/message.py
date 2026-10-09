from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, Text, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdentityMixin


class Message(IdentityMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at", "id"),
        CheckConstraint("role IN ('user','assistant')"),
        CheckConstraint("state IN ('processing','completed','failed','cancelled')"),
        ForeignKeyConstraint(
            ["conversation_id", "organization_id"],
            ["conversations.id", "conversations.organization_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("id", "conversation_id", "organization_id"),
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    conversation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    sanitized_text: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    policy_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    attachment_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
