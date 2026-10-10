from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdentityMixin, now


class CompanyRulePolicy(IdentityMixin, Base):
    """Company privacy policy, built-in toggles, custom rules, and optimistic versioning."""

    __tablename__ = "company_rule_policies"

    company_id: Mapped[object] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    builtins: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    custom_rules: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now, nullable=False
    )
