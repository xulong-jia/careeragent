"""add resume version target role

Revision ID: 20260621_0002
Revises: 20260621_0001
Create Date: 2026-06-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260621_0002"
down_revision: Union[str, None] = "20260621_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "resume_versions",
        sa.Column("target_role", sa.String(length=160), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("resume_versions", "target_role")
