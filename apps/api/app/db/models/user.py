from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdentityMixin


class User(IdentityMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("role IN ('employee', 'manager')", name="users_role_check"),
    )
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id"), index=True
    )
    email: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    failed_login_attempts: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(default=True)
