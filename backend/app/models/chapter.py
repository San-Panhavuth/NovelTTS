from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.audio_job import AudioJob
    from app.models.book import Book
    from app.models.segment import Segment


class Chapter(Base, TimestampMixin):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("book_id", "chapter_idx", name="uq_chapters_book_idx"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    book_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("books.id", ondelete="CASCADE"), index=True
    )
    chapter_idx: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), default="uploaded")

    book: Mapped[Book] = relationship(back_populates="chapters")
    segments: Mapped[list[Segment]] = relationship(back_populates="chapter", cascade="all, delete")
    audio_jobs: Mapped[list[AudioJob]] = relationship(
        back_populates="chapter", cascade="all, delete"
    )
