"""create phase two core tables

Revision ID: 20260621_0001
Revises:
Create Date: 2026-06-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260621_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resumes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=40), nullable=False),
        sa.Column("source_file_hash", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "job_descriptions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("company", sa.String(length=160), nullable=False),
        sa.Column("job_title", sa.String(length=200), nullable=False),
        sa.Column("location", sa.String(length=160), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "resume_versions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("resume_id", sa.String(length=64), nullable=False),
        sa.Column("version_name", sa.String(length=200), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("raw_text_preview", sa.Text(), nullable=False),
        sa.Column("structured_resume", sa.JSON(), nullable=False),
        sa.Column("extraction_status", sa.String(length=60), nullable=False),
        sa.Column("extraction_method", sa.String(length=120), nullable=False),
        sa.Column("extraction_warnings", sa.JSON(), nullable=False),
        sa.Column("risk_flags", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resume_versions_resume_id", "resume_versions", ["resume_id"])
    op.create_table(
        "job_profiles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("jd_id", sa.String(length=64), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("role_category", sa.String(length=160), nullable=False),
        sa.Column("required_skills", sa.JSON(), nullable=False),
        sa.Column("preferred_skills", sa.JSON(), nullable=False),
        sa.Column("responsibilities", sa.JSON(), nullable=False),
        sa.Column("business_scenarios", sa.JSON(), nullable=False),
        sa.Column("hidden_requirements", sa.JSON(), nullable=False),
        sa.Column("interview_focus", sa.JSON(), nullable=False),
        sa.Column("risk_level", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["jd_id"], ["job_descriptions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_profiles_jd_id", "job_profiles", ["jd_id"])
    op.create_table(
        "match_reports",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("resume_version_id", sa.String(length=64), nullable=False),
        sa.Column("jd_id", sa.String(length=64), nullable=False),
        sa.Column("job_profile_id", sa.String(length=64), nullable=True),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("dimension_scores", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("gaps", sa.JSON(), nullable=False),
        sa.Column("rewrite_priorities", sa.JSON(), nullable=False),
        sa.Column("risk_flags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["jd_id"], ["job_descriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_profile_id"], ["job_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resume_version_id"], ["resume_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_match_reports_jd_id", "match_reports", ["jd_id"])
    op.create_index("ix_match_reports_job_profile_id", "match_reports", ["job_profile_id"])
    op.create_index("ix_match_reports_resume_version_id", "match_reports", ["resume_version_id"])


def downgrade() -> None:
    op.drop_index("ix_match_reports_resume_version_id", table_name="match_reports")
    op.drop_index("ix_match_reports_job_profile_id", table_name="match_reports")
    op.drop_index("ix_match_reports_jd_id", table_name="match_reports")
    op.drop_table("match_reports")
    op.drop_index("ix_job_profiles_jd_id", table_name="job_profiles")
    op.drop_table("job_profiles")
    op.drop_index("ix_resume_versions_resume_id", table_name="resume_versions")
    op.drop_table("resume_versions")
    op.drop_table("job_descriptions")
    op.drop_table("resumes")
