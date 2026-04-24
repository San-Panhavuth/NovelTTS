from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.segment import Segment


class Character(Base, TimestampMixin):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    book_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("books.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)

    book: Mapped[Book] = relationship(back_populates="characters")
    segments: Mapped[list[Segment]] = relationship(back_populates="character")
