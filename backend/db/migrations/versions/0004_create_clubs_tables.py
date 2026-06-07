"""create clubs tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-07

"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clubs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "club_memberships",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("club_id", sa.BigInteger(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["club_id"], ["clubs.id"]),
        sa.PrimaryKeyConstraint("user_id", "club_id"),
    )
    op.create_index(
        "ix_club_memberships_club_id",
        "club_memberships",
        ["club_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_club_memberships_club_id", table_name="club_memberships")
    op.drop_table("club_memberships")
    op.drop_table("clubs")
