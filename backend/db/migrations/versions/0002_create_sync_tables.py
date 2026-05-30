"""create sync tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-30

"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("strava_activity_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("sport_type", sa.Text(), nullable=False),
        sa.Column("distance_meters", sa.Numeric(), nullable=False),
        sa.Column("moving_time_seconds", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "strava_activity_id"),
    )
    op.create_index(
        "ix_activities_user_start_date",
        "activities",
        ["user_id", "start_date"],
    )

    op.create_table(
        "sync_state",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("last_sync_completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("sync_state")
    op.drop_index("ix_activities_user_start_date", table_name="activities")
    op.drop_table("activities")
