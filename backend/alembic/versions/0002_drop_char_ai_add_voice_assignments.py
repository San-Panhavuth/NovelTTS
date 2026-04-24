"""0002_voice_assignments

Revision ID: 0002_voice_assignments
Revises: 0001_init
Create Date: 2026-04-24

Drop character_profiles + voice_requirements tables and per-character voice_id column.
Add voice_assignments table for 3-role (narration/dialogue/thought) per-user and per-book assignment.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_voice_assignments"
down_revision: str | None = "0001_init"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("voice_requirements")
    op.drop_table("character_profiles")

    op.drop_column("characters", "voice_id")

    op.create_table(
        "voice_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("book_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("narration_voice_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("dialogue_voice_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("thought_pitch_semitones", sa.Float(), nullable=False, server_default="-2.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "book_id", name="uq_voice_assignments_user_book"),
    )
    op.create_index("ix_voice_assignments_user_id", "voice_assignments", ["user_id"])
    op.create_index("ix_voice_assignments_book_id", "voice_assignments", ["book_id"])


def downgrade() -> None:
    op.drop_index("ix_voice_assignments_book_id", table_name="voice_assignments")
    op.drop_index("ix_voice_assignments_user_id", table_name="voice_assignments")
    op.drop_table("voice_assignments")

    op.add_column(
        "characters",
        sa.Column("voice_id", postgresql.UUID(as_uuid=False), nullable=True),
    )

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
