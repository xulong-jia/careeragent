"""extend bad case regression fields

Revision ID: 20260630_0017
Revises: 20260630_0016
Create Date: 2026-06-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260630_0017"
down_revision: Union[str, None] = "20260630_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("bad_cases") as batch_op:
        batch_op.add_column(sa.Column("root_cause", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("fix_strategy", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "tags",
                sa.JSON(),
                server_default=sa.text("'[]'"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "added_to_eval_set",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("verified_at", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column("regression_evaluation_run_id", sa.String(length=64), nullable=True)
        )
        batch_op.add_column(
            sa.Column("regression_evaluation_case_id", sa.String(length=64), nullable=True)
        )
        batch_op.create_index("ix_bad_cases_added_to_eval_set", ["added_to_eval_set"])


def downgrade() -> None:
    with op.batch_alter_table("bad_cases") as batch_op:
        batch_op.drop_index("ix_bad_cases_added_to_eval_set")
        batch_op.drop_column("regression_evaluation_case_id")
        batch_op.drop_column("regression_evaluation_run_id")
        batch_op.drop_column("verified_at")
        batch_op.drop_column("added_to_eval_set")
        batch_op.drop_column("tags")
        batch_op.drop_column("fix_strategy")
        batch_op.drop_column("root_cause")
