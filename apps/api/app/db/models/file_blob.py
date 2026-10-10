"""Private durable bytes for the small deployment; not manager-report content."""

from sqlalchemy import ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class FileBlob(Base):
    __tablename__ = "private_file_blobs"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    attachment_id: Mapped[object] = mapped_column(
        ForeignKey("attachments.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
