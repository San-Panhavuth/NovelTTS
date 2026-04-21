from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin


class Voice(Base, TimestampMixin):
    __tablename__ = "voices"
    __table_args__ = (UniqueConstraint("provider", "provider_id", name="uq_voices_provider_id"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64))
    provider_id: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(255))
    gender: Mapped[str | None] = mapped_column(String(64), nullable=True)
    locale: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pitch: Mapped[str | None] = mapped_column(String(64), nullable=True)
    age_group: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    energy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sample_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
