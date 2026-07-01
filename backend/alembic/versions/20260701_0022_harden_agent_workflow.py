"""harden agent workflow lifecycle

Revision ID: 20260701_0022
Revises: 20260701_0021
Create Date: 2026-07-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260701_0022"
down_revision: Union[str, None] = "20260701_0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "final_output_ref",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "run_config",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch_op.add_column(sa.Column("bad_case_id", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column(
                "bad_case_payload",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch_op.add_column(
            sa.Column("retry_attempt", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
        batch_op.create_index(
            "ix_agent_runs_bad_case_id",
            ["bad_case_id"],
            unique=False,
        )

    with op.batch_alter_table("agent_steps") as batch_op:
        batch_op.drop_constraint("uq_agent_steps_run_id_step_order", type_="unique")
        batch_op.add_column(
            sa.Column("attempt", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.add_column(
            sa.Column(
                "run_config",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "privacy_safe_payload",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch_op.create_unique_constraint(
            "uq_agent_steps_run_id_step_order_attempt",
            ["run_id", "step_order", "attempt"],
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_steps") as batch_op:
        batch_op.drop_constraint("uq_agent_steps_run_id_step_order_attempt", type_="unique")
        batch_op.drop_column("privacy_safe_payload")
        batch_op.drop_column("run_config")
        batch_op.drop_column("attempt")
        batch_op.create_unique_constraint(
            "uq_agent_steps_run_id_step_order",
            ["run_id", "step_order"],
        )

    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.drop_index("ix_agent_runs_bad_case_id")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("retry_attempt")
        batch_op.drop_column("bad_case_payload")
        batch_op.drop_column("bad_case_id")
        batch_op.drop_column("run_config")
        batch_op.drop_column("final_output_ref")
