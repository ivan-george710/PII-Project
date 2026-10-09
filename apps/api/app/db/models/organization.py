from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdentityMixin


class Organization(IdentityMixin, Base):
    __tablename__ = "organizations"
    name: Mapped[str] = mapped_column(String(120))
