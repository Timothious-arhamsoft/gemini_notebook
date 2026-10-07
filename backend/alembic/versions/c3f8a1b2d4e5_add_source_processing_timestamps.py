"""add_source_processing_timestamps

Revision ID: c3f8a1b2d4e5
Revises: 211ec1cba57e
Create Date: 2026-10-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c3f8a1b2d4e5"
down_revision: Union[str, Sequence[str], None] = "211ec1cba57e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("processing_failed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("processing_timings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sources", "processing_timings")
    op.drop_column("sources", "processing_failed_at")
    op.drop_column("sources", "processing_completed_at")
    op.drop_column("sources", "processing_started_at")
