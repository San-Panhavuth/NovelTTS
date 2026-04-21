from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.character import Character


class VoiceRequirement(Base, TimestampMixin):
    __tablename__ = "voice_requirements"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    character_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("characters.id", ondelete="CASCADE"), unique=True
    )
    pitch: Mapped[str | None] = mapped_column(String(64), nullable=True)
    age_group: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pacing: Mapped[str | None] = mapped_column(String(64), nullable=True)
    energy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    avoid: Mapped[dict] = mapped_column(JSONB)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    character: Mapped[Character] = relationship(back_populates="voice_requirement")
