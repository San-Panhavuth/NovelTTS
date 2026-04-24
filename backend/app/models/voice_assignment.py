from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin


class VoiceAssignment(Base, TimestampMixin):
    """Per-user default or per-book override for the three voice roles."""

    __tablename__ = "voice_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_voice_assignments_user_book"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # null book_id = user-level default
    book_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("books.id", ondelete="CASCADE"), nullable=True, index=True
    )
    narration_voice_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    dialogue_voice_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    # semitones offset applied to thought segments (negative = lower pitch)
    thought_pitch_semitones: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="-2.0"
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False)  # "user" | "book"
