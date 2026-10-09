from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, now


class ManagerAssignment(Base):
    __tablename__ = "manager_assignments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["employee_id", "organization_id"],
            ["users.id", "users.organization_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["manager_id", "organization_id"],
            ["users.id", "users.organization_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("employee_id <> manager_id"),
    )
    employee_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    manager_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )
