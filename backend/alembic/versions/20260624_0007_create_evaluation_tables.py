"""create evaluation tables

Revision ID: 20260624_0007
Revises: 20260624_0006
Create Date: 2026-06-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260624_0007"
down_revision: Union[str, None] = "20260624_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("module", sa.String(length=40), nullable=False),
        sa.Column("dataset_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("run_config", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evaluation_runs_module", "evaluation_runs", ["module"])
    op.create_index(
        "ix_evaluation_runs_dataset_name",
        "evaluation_runs",
        ["dataset_name"],
    )
    op.create_index("ix_evaluation_runs_status", "evaluation_runs", ["status"])

    op.create_table(
        "evaluation_cases",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("module", sa.String(length=40), nullable=False),
        sa.Column("dataset_name", sa.String(length=120), nullable=False),
        sa.Column("case_name", sa.String(length=200), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("expected_output", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("bad_case_id", sa.String(length=64), nullable=True),
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
        sa.ForeignKeyConstraint(["bad_case_id"], ["bad_cases.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evaluation_cases_module", "evaluation_cases", ["module"])
    op.create_index(
        "ix_evaluation_cases_dataset_name",
        "evaluation_cases",
        ["dataset_name"],
    )
    op.create_index(
        "ix_evaluation_cases_case_name",
        "evaluation_cases",
        ["case_name"],
    )
    op.create_index(
        "ix_evaluation_cases_source_type",
        "evaluation_cases",
        ["source_type"],
    )
    op.create_index(
        "ix_evaluation_cases_bad_case_id",
        "evaluation_cases",
        ["bad_case_id"],
    )

    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("case_id", sa.String(length=64), nullable=False),
        sa.Column("module", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("actual_output", sa.JSON(), nullable=False),
        sa.Column("expected_output", sa.JSON(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["case_id"], ["evaluation_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evaluation_results_run_id", "evaluation_results", ["run_id"])
    op.create_index("ix_evaluation_results_case_id", "evaluation_results", ["case_id"])
    op.create_index("ix_evaluation_results_module", "evaluation_results", ["module"])
    op.create_index("ix_evaluation_results_status", "evaluation_results", ["status"])


def downgrade() -> None:
    op.drop_index("ix_evaluation_results_status", table_name="evaluation_results")
    op.drop_index("ix_evaluation_results_module", table_name="evaluation_results")
    op.drop_index("ix_evaluation_results_case_id", table_name="evaluation_results")
    op.drop_index("ix_evaluation_results_run_id", table_name="evaluation_results")
    op.drop_table("evaluation_results")

    op.drop_index("ix_evaluation_cases_bad_case_id", table_name="evaluation_cases")
    op.drop_index("ix_evaluation_cases_source_type", table_name="evaluation_cases")
    op.drop_index("ix_evaluation_cases_case_name", table_name="evaluation_cases")
    op.drop_index("ix_evaluation_cases_dataset_name", table_name="evaluation_cases")
    op.drop_index("ix_evaluation_cases_module", table_name="evaluation_cases")
    op.drop_table("evaluation_cases")

    op.drop_index("ix_evaluation_runs_status", table_name="evaluation_runs")
    op.drop_index("ix_evaluation_runs_dataset_name", table_name="evaluation_runs")
    op.drop_index("ix_evaluation_runs_module", table_name="evaluation_runs")
    op.drop_table("evaluation_runs")
