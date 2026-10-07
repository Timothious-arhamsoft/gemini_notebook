"""fix_chat_message_timestamp_ties

Revision ID: d4a1c9e8f2b0
Revises: c3f8a1b2d4e5
Create Date: 2026-10-07 20:00:00.000000

User + assistant rows created in the same DB transaction previously shared an
identical created_at (PostgreSQL now() is transaction-start time). Listing by
created_at alone then returned those pairs in non-deterministic order.

For the common case — exactly one user and one assistant sharing a timestamp —
nudge the assistant forward by 1 microsecond so chronological ORDER BY is stable.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "d4a1c9e8f2b0"
down_revision: Union[str, Sequence[str], None] = "c3f8a1b2d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        WITH tied_pairs AS (
            SELECT notebook_id, created_at
            FROM chat_messages
            GROUP BY notebook_id, created_at
            HAVING COUNT(*) = 2
               AND COUNT(*) FILTER (WHERE role = 'user') = 1
               AND COUNT(*) FILTER (WHERE role = 'assistant') = 1
        )
        UPDATE chat_messages AS m
        SET created_at = m.created_at + interval '1 microsecond'
        FROM tied_pairs AS p
        WHERE m.notebook_id = p.notebook_id
          AND m.created_at = p.created_at
          AND m.role = 'assistant'
        """
    )


def downgrade() -> None:
    # Irreversible data repair; timestamps remain valid chronologically.
    pass
