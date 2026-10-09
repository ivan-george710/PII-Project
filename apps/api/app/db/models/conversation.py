from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKeyConstraint, Index, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdentityMixin


class Conversation(IdentityMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_owner_updated", "organization_id", "employee_id", "updated_at", "id"),
        ForeignKeyConstraint(
            ["employee_id", "organization_id"],
            ["users.id", "users.organization_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("id", "organization_id"),
        UniqueConstraint("id", "employee_id", "organization_id"),
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    employee_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
