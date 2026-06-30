"""add application agent run link

Revision ID: 20260630_0015
Revises: 20260625_0014
Create Date: 2026-06-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260630_0015"
down_revision: Union[str, None] = "20260625_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("applications") as batch_op:
        batch_op.add_column(sa.Column("agent_run_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            "fk_applications_agent_run_id_agent_runs",
            "agent_runs",
            ["agent_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_applications_agent_run_id", ["agent_run_id"])


def downgrade() -> None:
    with op.batch_alter_table("applications") as batch_op:
        batch_op.drop_index("ix_applications_agent_run_id")
        batch_op.drop_constraint(
            "fk_applications_agent_run_id_agent_runs",
            type_="foreignkey",
        )
        batch_op.drop_column("agent_run_id")
