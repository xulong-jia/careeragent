"""add rag chunk embedding persistence

Revision ID: 20260701_0019
Revises: 20260630_0018
Create Date: 2026-07-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260701_0019"
down_revision: Union[str, None] = "20260630_0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("rag_chunks") as batch_op:
        batch_op.add_column(sa.Column("embedding_vector", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("embedding_provider", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("embedding_model", sa.String(length=160), nullable=True))
        batch_op.add_column(sa.Column("embedding_dim", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("embedding_version", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("embedding_created_at", sa.DateTime(), nullable=True))
    with op.batch_alter_table("rag_answer_runs") as batch_op:
        batch_op.alter_column(
            "retrieval_mode",
            existing_type=sa.String(length=40),
            server_default="lexical",
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("rag_answer_runs") as batch_op:
        batch_op.alter_column(
            "retrieval_mode",
            existing_type=sa.String(length=40),
            server_default="deterministic_lexical",
            existing_nullable=False,
        )
    with op.batch_alter_table("rag_chunks") as batch_op:
        batch_op.drop_column("embedding_created_at")
        batch_op.drop_column("embedding_version")
        batch_op.drop_column("embedding_dim")
        batch_op.drop_column("embedding_model")
        batch_op.drop_column("embedding_provider")
        batch_op.drop_column("embedding_vector")
