"""create project rewrites

Revision ID: 20260624_0011
Revises: 20260624_0010
Create Date: 2026-06-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260624_0011"
down_revision: Union[str, None] = "20260624_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_rewrites",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("jd_id", sa.String(length=64), nullable=False),
        sa.Column("resume_version_id", sa.String(length=64), nullable=True),
        sa.Column("match_report_id", sa.String(length=64), nullable=True),
        sa.Column("profile_id", sa.String(length=64), nullable=True),
        sa.Column("matched_points", sa.JSON(), nullable=False),
        sa.Column("missing_points", sa.JSON(), nullable=False),
        sa.Column("evidence_required", sa.JSON(), nullable=False),
        sa.Column("rewritten_bullets", sa.JSON(), nullable=False),
        sa.Column("forbidden_changes", sa.JSON(), nullable=False),
        sa.Column("risk_flags", sa.JSON(), nullable=False),
        sa.Column(
            "rewrite_strategy",
            sa.String(length=120),
            server_default="deterministic_project_rewrite_v1",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["jd_id"],
            ["job_descriptions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resume_version_id"],
            ["resume_versions.id"],
            ondelete="SET NULL",
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_project_rewrites_project_id",
        "project_rewrites",
        ["project_id"],
    )
    op.create_index(
        "ix_project_rewrites_jd_id",
        "project_rewrites",
        ["jd_id"],
    )
    op.create_index(
        "ix_project_rewrites_resume_version_id",
        "project_rewrites",
        ["resume_version_id"],
    )
    op.create_index(
        "ix_project_rewrites_match_report_id",
        "project_rewrites",
        ["match_report_id"],
    )
    op.create_index(
        "ix_project_rewrites_profile_id",
        "project_rewrites",
        ["profile_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_rewrites_profile_id", table_name="project_rewrites")
    op.drop_index("ix_project_rewrites_match_report_id", table_name="project_rewrites")
    op.drop_index("ix_project_rewrites_resume_version_id", table_name="project_rewrites")
    op.drop_index("ix_project_rewrites_jd_id", table_name="project_rewrites")
    op.drop_index("ix_project_rewrites_project_id", table_name="project_rewrites")
    op.drop_table("project_rewrites")
