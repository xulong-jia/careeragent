"""create profiles

Revision ID: 20260624_0009
Revises: 20260624_0008
Create Date: 2026-06-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260624_0009"
down_revision: Union[str, None] = "20260624_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("target_roles", sa.JSON(), nullable=False),
        sa.Column("target_industries", sa.JSON(), nullable=False),
        sa.Column("target_locations", sa.JSON(), nullable=False),
        sa.Column("skill_map", sa.JSON(), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.Column("source_resume_version_id", sa.String(length=64), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["source_resume_version_id"],
            ["resume_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_profiles_user_id", "profiles", ["user_id"])
    op.create_index(
        "ix_profiles_source_resume_version_id",
        "profiles",
        ["source_resume_version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_profiles_source_resume_version_id", table_name="profiles")
    op.drop_index("ix_profiles_user_id", table_name="profiles")
    op.drop_table("profiles")
