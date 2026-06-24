"""add resume parse status and risk report

Revision ID: 20260624_0008
Revises: 20260624_0007
Create Date: 2026-06-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260624_0008"
down_revision: Union[str, None] = "20260624_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "resumes",
        sa.Column(
            "parse_status",
            sa.String(length=40),
            nullable=False,
            server_default="parsed",
        ),
    )
    op.add_column(
        "resume_versions",
        sa.Column(
            "risk_report",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("resume_versions", "risk_report")
    op.drop_column("resumes", "parse_status")
