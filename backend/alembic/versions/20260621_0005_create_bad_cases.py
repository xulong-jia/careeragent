"""create bad cases

Revision ID: 20260621_0005
Revises: 20260621_0004
Create Date: 2026-06-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260621_0005"
down_revision: Union[str, None] = "20260621_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bad_cases",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=60), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("expected_behavior", sa.Text(), nullable=True),
        sa.Column("actual_behavior", sa.Text(), nullable=True),
        sa.Column("suggested_fix", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bad_cases_source_type", "bad_cases", ["source_type"])
    op.create_index("ix_bad_cases_source_id", "bad_cases", ["source_id"])
    op.create_index("ix_bad_cases_status", "bad_cases", ["status"])
    op.create_index("ix_bad_cases_severity", "bad_cases", ["severity"])
    op.create_index("ix_bad_cases_category", "bad_cases", ["category"])
    op.create_index(
        "ix_bad_cases_source_type_source_id",
        "bad_cases",
        ["source_type", "source_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_bad_cases_source_type_source_id", table_name="bad_cases")
    op.drop_index("ix_bad_cases_category", table_name="bad_cases")
    op.drop_index("ix_bad_cases_severity", table_name="bad_cases")
    op.drop_index("ix_bad_cases_status", table_name="bad_cases")
    op.drop_index("ix_bad_cases_source_id", table_name="bad_cases")
    op.drop_index("ix_bad_cases_source_type", table_name="bad_cases")
    op.drop_table("bad_cases")
