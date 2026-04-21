from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.character import Character


class CharacterProfile(Base, TimestampMixin):
    __tablename__ = "character_profiles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    character_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("characters.id", ondelete="CASCADE"), unique=True
    )
    age: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(64), nullable=True)
    personality: Mapped[dict] = mapped_column(JSONB)
    speech_style: Mapped[dict] = mapped_column(JSONB)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    voice_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    character: Mapped[Character] = relationship(back_populates="profile")
