from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, now


class PiiEvent(Base):
    """Persisted submission PII findings/actions for manager reporting and auditing."""

    __tablename__ = "pii_events"

    id: Mapped[object] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[object] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submission_id: Mapped[object] = mapped_column(Uuid, nullable=False, index=True)
    employee_id: Mapped[object] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    findings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "submission_id",
            "policy_version",
            name="uq_pii_events_company_submission_version",
        ),
        Index("ix_pii_events_company_employee_time", "company_id", "employee_id", "occurred_at"),
    )
