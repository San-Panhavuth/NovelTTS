from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.book import Book


class PronunciationEntry(Base, TimestampMixin):
    __tablename__ = "pronunciation_entries"
    __table_args__ = (UniqueConstraint("book_id", "term", name="uq_pronunciations_book_term"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    book_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("books.id", ondelete="CASCADE"), index=True
    )
    term: Mapped[str] = mapped_column(String(255))
    phoneme: Mapped[str] = mapped_column(String(255))
    language_code: Mapped[str | None] = mapped_column(String(16), nullable=True)

    book: Mapped[Book] = relationship(back_populates="pronunciations")
