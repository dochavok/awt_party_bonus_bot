"""Item class counts (requirements section 11, IC-1, IC-2).

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "character_item_count",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "character_id",
            sa.Integer,
            sa.ForeignKey("character.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_class_id", sa.String, nullable=False),
        sa.Column("count", sa.Integer, nullable=False),
        sa.UniqueConstraint("character_id", "item_class_id"),
        sa.CheckConstraint("count BETWEEN 1 AND 30", name="ck_character_item_count_count"),
    )


def downgrade() -> None:
    op.drop_table("character_item_count")
