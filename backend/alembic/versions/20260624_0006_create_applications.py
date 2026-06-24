"""create applications

Revision ID: 20260624_0006
Revises: 20260621_0005
Create Date: 2026-06-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260624_0006"
down_revision: Union[str, None] = "20260621_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("company", sa.String(length=160), nullable=False),
        sa.Column("role_title", sa.String(length=200), nullable=False),
        sa.Column("role_category", sa.String(length=160), nullable=True),
        sa.Column("jd_id", sa.String(length=64), nullable=True),
        sa.Column("resume_version_id", sa.String(length=64), nullable=True),
        sa.Column("match_report_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("apply_date", sa.Date(), nullable=True),
        sa.Column("next_step_date", sa.Date(), nullable=True),
        sa.Column("interview_notes", sa.Text(), nullable=True),
        sa.Column("reflection", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
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
        sa.ForeignKeyConstraint(["jd_id"], ["job_descriptions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["match_report_id"],
            ["match_reports.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resume_version_id"],
            ["resume_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_applications_company", "applications", ["company"])
    op.create_index("ix_applications_jd_id", "applications", ["jd_id"])
    op.create_index("ix_applications_match_report_id", "applications", ["match_report_id"])
    op.create_index("ix_applications_resume_version_id", "applications", ["resume_version_id"])
    op.create_index("ix_applications_role_category", "applications", ["role_category"])
    op.create_index("ix_applications_status", "applications", ["status"])


def downgrade() -> None:
    op.drop_index("ix_applications_status", table_name="applications")
    op.drop_index("ix_applications_role_category", table_name="applications")
    op.drop_index("ix_applications_resume_version_id", table_name="applications")
    op.drop_index("ix_applications_match_report_id", table_name="applications")
    op.drop_index("ix_applications_jd_id", table_name="applications")
    op.drop_index("ix_applications_company", table_name="applications")
    op.drop_table("applications")
