"""0001_init

Revision ID: 0001_init
Revises:
Create Date: 2026-04-21 16:35:00

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_init"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


segment_type_enum = sa.Enum("narration", "dialogue", "thought", name="segmenttype")
job_status_enum = sa.Enum("queued", "processing", "completed", "failed", name="jobstatus")


def upgrade() -> None:
    bind = op.get_bind()
    segment_type_enum.create(bind, checkfirst=True)
    job_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "books",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("author", sa.String(length=512), nullable=True),
        sa.Column("origin_language", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_books_user_id", "books", ["user_id"])

    op.create_table(
        "chapters",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("book_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("chapter_idx", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="uploaded"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("book_id", "chapter_idx", name="uq_chapters_book_idx"),
    )
    op.create_index("ix_chapters_book_id", "chapters", ["book_id"])

    op.create_table(
        "characters",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("book_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=True),
        sa.Column("voice_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_characters_book_id", "characters", ["book_id"])

    op.create_table(
        "voices",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("gender", sa.String(length=64), nullable=True),
        sa.Column("locale", sa.String(length=32), nullable=True),
        sa.Column("pitch", sa.String(length=64), nullable=True),
        sa.Column("age_group", sa.String(length=64), nullable=True),
        sa.Column("tone", sa.String(length=64), nullable=True),
        sa.Column("energy", sa.String(length=64), nullable=True),
        sa.Column("sample_url", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider", "provider_id", name="uq_voices_provider_id"),
    )

    op.create_table(
        "segments",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("segment_idx", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("type", segment_type_enum, nullable=False, server_default="narration"),
        sa.Column("character_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("audio_url", sa.String(length=1024), nullable=True),
        sa.Column("content_hash", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("chapter_id", "segment_idx", name="uq_segments_chapter_idx"),
    )
    op.create_index("ix_segments_chapter_id", "segments", ["chapter_id"])

    op.create_table(
        "character_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("character_id", postgresql.UUID(as_uuid=False), nullable=False, unique=True),
        sa.Column("age", sa.String(length=64), nullable=True),
        sa.Column("gender", sa.String(length=64), nullable=True),
        sa.Column("personality", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("speech_style", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=True),
        sa.Column("voice_notes", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "voice_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("character_id", postgresql.UUID(as_uuid=False), nullable=False, unique=True),
        sa.Column("pitch", sa.String(length=64), nullable=True),
        sa.Column("age_group", sa.String(length=64), nullable=True),
        sa.Column("tone", sa.String(length=64), nullable=True),
        sa.Column("pacing", sa.String(length=64), nullable=True),
        sa.Column("energy", sa.String(length=64), nullable=True),
        sa.Column("avoid", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "audio_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("status", job_status_enum, nullable=False, server_default="queued"),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("output_url", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_audio_jobs_chapter_id", "audio_jobs", ["chapter_id"])

    op.create_table(
        "pronunciation_entries",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("book_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("term", sa.String(length=255), nullable=False),
        sa.Column("phoneme", sa.String(length=255), nullable=False),
        sa.Column("language_code", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("book_id", "term", name="uq_pronunciations_book_term"),
    )
    op.create_index("ix_pronunciation_entries_book_id", "pronunciation_entries", ["book_id"])


def downgrade() -> None:
    op.drop_index("ix_pronunciation_entries_book_id", table_name="pronunciation_entries")
    op.drop_table("pronunciation_entries")

    op.drop_index("ix_audio_jobs_chapter_id", table_name="audio_jobs")
    op.drop_table("audio_jobs")

    op.drop_table("voice_requirements")
    op.drop_table("character_profiles")

    op.drop_index("ix_segments_chapter_id", table_name="segments")
    op.drop_table("segments")

    op.drop_table("voices")

    op.drop_index("ix_characters_book_id", table_name="characters")
    op.drop_table("characters")

    op.drop_index("ix_chapters_book_id", table_name="chapters")
    op.drop_table("chapters")

    op.drop_index("ix_books_user_id", table_name="books")
    op.drop_table("books")

    op.drop_table("users")

    bind = op.get_bind()
    job_status_enum.drop(bind, checkfirst=True)
    segment_type_enum.drop(bind, checkfirst=True)
