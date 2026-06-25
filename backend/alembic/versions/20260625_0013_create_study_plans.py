"""create study plans

Revision ID: 20260625_0013
Revises: 20260624_0012
Create Date: 2026-06-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260625_0013"
down_revision: Union[str, None] = "20260624_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "study_plans",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column(
            "user_id",
            sa.String(length=64),
            server_default="default",
            nullable=False,
        ),
        sa.Column("match_report_id", sa.String(length=64), nullable=True),
        sa.Column("profile_id", sa.String(length=64), nullable=True),
        sa.Column("project_rewrite_id", sa.String(length=64), nullable=True),
        sa.Column("target_role", sa.String(length=160), nullable=False),
        sa.Column("source_refs", sa.JSON(), nullable=False),
        sa.Column("phases", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=40),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'archived')",
            name="ck_study_plans_status",
        ),
        sa.ForeignKeyConstraint(
            ["match_report_id"],
            ["match_reports.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_rewrite_id"],
            ["project_rewrites.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_study_plans_user_id", "study_plans", ["user_id"])
    op.create_index(
        "ix_study_plans_match_report_id",
        "study_plans",
        ["match_report_id"],
    )
    op.create_index("ix_study_plans_profile_id", "study_plans", ["profile_id"])
    op.create_index(
        "ix_study_plans_project_rewrite_id",
        "study_plans",
        ["project_rewrite_id"],
    )
    op.create_index("ix_study_plans_target_role", "study_plans", ["target_role"])


def downgrade() -> None:
    op.drop_index("ix_study_plans_target_role", table_name="study_plans")
    op.drop_index("ix_study_plans_project_rewrite_id", table_name="study_plans")
    op.drop_index("ix_study_plans_profile_id", table_name="study_plans")
    op.drop_index("ix_study_plans_match_report_id", table_name="study_plans")
    op.drop_index("ix_study_plans_user_id", table_name="study_plans")
    op.drop_table("study_plans")
