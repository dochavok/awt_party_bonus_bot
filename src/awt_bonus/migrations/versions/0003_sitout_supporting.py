"""Supporting sit-outs (requirements section 10, SE-7).

Existing sit-outs become plain ones (SE-2).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sit_out",
        sa.Column("supporting", sa.Boolean, nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    with op.batch_alter_table("sit_out") as batch:
        batch.drop_column("supporting")
