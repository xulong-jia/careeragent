"""create rag answer runs

Revision ID: 20260625_0014
Revises: 20260625_0013
Create Date: 2026-06-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260625_0014"
down_revision: Union[str, None] = "20260625_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_answer_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=True),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column(
            "retrieval_mode",
            sa.String(length=40),
            nullable=False,
            server_default="deterministic_lexical",
        ),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("answer_type", sa.String(length=40), nullable=False),
        sa.Column("grounded", sa.Boolean(), nullable=False),
        sa.Column("uncertainty", sa.String(length=80), nullable=False),
        sa.Column("evidence_summary", sa.JSON(), nullable=False),
        sa.Column("citations_json", sa.JSON(), nullable=False),
        sa.Column("source_refs_json", sa.JSON(), nullable=False),
        sa.Column("retrieval_debug_json", sa.JSON(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rag_answer_runs_user_id", "rag_answer_runs", ["user_id"])
    op.create_index("ix_rag_answer_runs_grounded", "rag_answer_runs", ["grounded"])
    op.create_index(
        "ix_rag_answer_runs_uncertainty",
        "rag_answer_runs",
        ["uncertainty"],
    )
    op.create_index(
        "ix_rag_answer_runs_retrieval_mode",
        "rag_answer_runs",
        ["retrieval_mode"],
    )


def downgrade() -> None:
    op.drop_index("ix_rag_answer_runs_retrieval_mode", table_name="rag_answer_runs")
    op.drop_index("ix_rag_answer_runs_uncertainty", table_name="rag_answer_runs")
    op.drop_index("ix_rag_answer_runs_grounded", table_name="rag_answer_runs")
    op.drop_index("ix_rag_answer_runs_user_id", table_name="rag_answer_runs")
    op.drop_table("rag_answer_runs")
