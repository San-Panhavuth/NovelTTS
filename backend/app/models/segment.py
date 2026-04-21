from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import SegmentType
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.chapter import Chapter
    from app.models.character import Character


class Segment(Base, TimestampMixin):
    __tablename__ = "segments"
    __table_args__ = (
        UniqueConstraint("chapter_id", "segment_idx", name="uq_segments_chapter_idx"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    chapter_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    segment_idx: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    type: Mapped[SegmentType] = mapped_column(Enum(SegmentType), default=SegmentType.NARRATION)
    character_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("characters.id", ondelete="SET NULL"), nullable=True
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    chapter: Mapped[Chapter] = relationship(back_populates="segments")
    character: Mapped[Character | None] = relationship(back_populates="segments")
