"""The first schema (requirements section 11).

Revision ID: 0001
Revises:
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from awt_bonus.schema import UTCDateTime

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "character",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("discord_user_id", sa.BigInteger, nullable=False),
        sa.Column("name", sa.String(collation="NOCASE"), nullable=False, unique=True),
        sa.Column("level", sa.Integer, nullable=True),
        sa.Column("level_updated_at", UTCDateTime, nullable=True),
    )
    op.create_index("ix_character_discord_user_id", "character", ["discord_user_id"])
    op.create_table(
        "player",
        sa.Column("discord_user_id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column(
            "current_character_id",
            sa.Integer,
            sa.ForeignKey("character.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_table(
        "character_entry",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "character_id",
            sa.Integer,
            sa.ForeignKey("character.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entry_id", sa.String, nullable=False),
        sa.UniqueConstraint("character_id", "entry_id"),
    )
    op.create_index("ix_character_entry_entry_id", "character_entry", ["entry_id"])
    op.create_table(
        "character_guild",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "character_id",
            sa.Integer,
            sa.ForeignKey("character.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("guild_id", sa.String, nullable=False),
        sa.Column("joined_at", UTCDateTime, nullable=False),
        sa.UniqueConstraint("character_id", "guild_id"),
    )
    op.create_table(
        "sit_out",
        sa.Column("discord_user_id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column("until", UTCDateTime, nullable=False),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("actor_user_id", sa.BigInteger, nullable=False),
        sa.Column("character_id", sa.Integer, nullable=False),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("before_json", sa.Text, nullable=True),
        sa.Column("after_json", sa.Text, nullable=True),
        sa.Column("at", UTCDateTime, nullable=False),
    )
    op.create_index("ix_audit_log_character_id", "audit_log", ["character_id"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("sit_out")
    op.drop_table("character_guild")
    op.drop_table("character_entry")
    op.drop_table("player")
    op.drop_table("character")
