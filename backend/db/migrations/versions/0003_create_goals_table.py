"""create goals table

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-05

"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "yearly_running_goal_km",
            sa.Numeric(),
            nullable=False,
            server_default="365",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "yearly_running_goal_km > 0 AND yearly_running_goal_km <= 100000",
            name="ck_goals_yearly_running_goal_km",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.execute(sa.text("INSERT INTO goals (user_id) SELECT id FROM users"))


def downgrade() -> None:
    op.drop_table("goals")
