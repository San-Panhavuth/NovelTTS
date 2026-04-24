from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import JobStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.chapter import Chapter


class AudioJob(Base, TimestampMixin):
    __tablename__ = "audio_jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    chapter_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(
            JobStatus,
            name="jobstatus",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=JobStatus.QUEUED,
    )
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    chapter: Mapped[Chapter] = relationship(back_populates="audio_jobs")
