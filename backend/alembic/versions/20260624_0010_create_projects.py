"""create projects

Revision ID: 20260624_0010
Revises: 20260624_0009
Create Date: 2026-06-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260624_0010"
down_revision: Union[str, None] = "20260624_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("profile_id", sa.String(length=64), nullable=True),
        sa.Column("resume_version_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=160), nullable=True),
        sa.Column("period", sa.String(length=160), nullable=True),
        sa.Column("background", sa.Text(), nullable=True),
        sa.Column("tech_stack", sa.JSON(), nullable=False),
        sa.Column("responsibilities", sa.JSON(), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
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
            "status IN ('active', 'archived')",
            name="ck_projects_status",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resume_version_id"],
            ["resume_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"])
    op.create_index("ix_projects_profile_id", "projects", ["profile_id"])
    op.create_index("ix_projects_resume_version_id", "projects", ["resume_version_id"])
    op.create_index("ix_projects_status", "projects", ["status"])


def downgrade() -> None:
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_index("ix_projects_resume_version_id", table_name="projects")
    op.drop_index("ix_projects_profile_id", table_name="projects")
    op.drop_index("ix_projects_user_id", table_name="projects")
    op.drop_table("projects")
