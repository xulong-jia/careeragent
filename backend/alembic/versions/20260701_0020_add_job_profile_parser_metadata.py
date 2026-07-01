"""add job profile parser metadata

Revision ID: 20260701_0020
Revises: 20260701_0019
Create Date: 2026-07-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260701_0020"
down_revision: Union[str, None] = "20260701_0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("job_profiles") as batch_op:
        batch_op.add_column(
            sa.Column("parse_confidence", sa.Float(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
        )
        batch_op.add_column(
            sa.Column("warnings", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
        )
        batch_op.add_column(
            sa.Column(
                "parser_metadata",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("job_profiles") as batch_op:
        batch_op.drop_column("parser_metadata")
        batch_op.drop_column("warnings")
        batch_op.drop_column("evidence")
        batch_op.drop_column("parse_confidence")
