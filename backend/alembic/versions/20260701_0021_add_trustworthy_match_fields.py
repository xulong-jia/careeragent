"""add trustworthy match and rewrite fields

Revision ID: 20260701_0021
Revises: 20260701_0020
Create Date: 2026-07-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260701_0021"
down_revision: Union[str, None] = "20260701_0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("match_reports") as batch_op:
        batch_op.add_column(
            sa.Column(
                "recommended_projects",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "score_breakdown",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "scoring_method",
                sa.String(length=120),
                nullable=False,
                server_default="deterministic_trustworthy_match_v1",
            )
        )
        batch_op.add_column(
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0")
        )

    with op.batch_alter_table("project_rewrites") as batch_op:
        batch_op.add_column(
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("project_rewrites") as batch_op:
        batch_op.drop_column("confidence")

    with op.batch_alter_table("match_reports") as batch_op:
        batch_op.drop_column("confidence")
        batch_op.drop_column("scoring_method")
        batch_op.drop_column("score_breakdown")
        batch_op.drop_column("recommended_projects")
