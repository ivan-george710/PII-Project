from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKeyConstraint, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdentityMixin


class Conversation(IdentityMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["employee_id", "organization_id"],
            ["users.id", "users.organization_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("id", "organization_id"),
        UniqueConstraint("id", "employee_id", "organization_id"),
    )
    organization_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    employee_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
