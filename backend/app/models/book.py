from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.chapter import Chapter
    from app.models.character import Character
    from app.models.pronunciation_entry import PronunciationEntry
    from app.models.user import User


class Book(Base, TimestampMixin):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(512))
    author: Mapped[str | None] = mapped_column(String(512), nullable=True)
    origin_language: Mapped[str | None] = mapped_column(String(32), nullable=True)

    user: Mapped[User] = relationship(back_populates="books")
    chapters: Mapped[list[Chapter]] = relationship(back_populates="book", cascade="all, delete")
    characters: Mapped[list[Character]] = relationship(back_populates="book", cascade="all, delete")
    pronunciations: Mapped[list[PronunciationEntry]] = relationship(
        back_populates="book", cascade="all, delete"
    )
