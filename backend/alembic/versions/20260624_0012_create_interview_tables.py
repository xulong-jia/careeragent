"""create interview tables

Revision ID: 20260624_0012
Revises: 20260624_0011
Create Date: 2026-06-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260624_0012"
down_revision: Union[str, None] = "20260624_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interview_questions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column(
            "user_id",
            sa.String(length=64),
            server_default="default",
            nullable=False,
        ),
        sa.Column("jd_id", sa.String(length=64), nullable=False),
        sa.Column("resume_version_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("project_rewrite_id", sa.String(length=64), nullable=True),
        sa.Column("question_type", sa.String(length=80), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_points", sa.JSON(), nullable=False),
        sa.Column("source_refs", sa.JSON(), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "question_type IN ("
            "'project_deep_dive', "
            "'technical_depth', "
            "'jd_skill_check', "
            "'risk_or_gap_explanation', "
            "'behavior_or_collaboration', "
            "'resume_challenge'"
            ")",
            name="ck_interview_questions_question_type",
        ),
        sa.CheckConstraint(
            "difficulty IN ('easy', 'medium', 'hard')",
            name="ck_interview_questions_difficulty",
        ),
        sa.ForeignKeyConstraint(
            ["jd_id"],
            ["job_descriptions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resume_version_id"],
            ["resume_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_rewrite_id"],
            ["project_rewrites.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_interview_questions_user_id",
        "interview_questions",
        ["user_id"],
    )
    op.create_index(
        "ix_interview_questions_jd_id",
        "interview_questions",
        ["jd_id"],
    )
    op.create_index(
        "ix_interview_questions_resume_version_id",
        "interview_questions",
        ["resume_version_id"],
    )
    op.create_index(
        "ix_interview_questions_project_id",
        "interview_questions",
        ["project_id"],
    )
    op.create_index(
        "ix_interview_questions_project_rewrite_id",
        "interview_questions",
        ["project_rewrite_id"],
    )
    op.create_index(
        "ix_interview_questions_question_type",
        "interview_questions",
        ["question_type"],
    )
    op.create_index(
        "ix_interview_questions_difficulty",
        "interview_questions",
        ["difficulty"],
    )

    op.create_table(
        "interview_answers",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("question_id", sa.String(length=64), nullable=False),
        sa.Column(
            "user_id",
            sa.String(length=64),
            server_default="default",
            nullable=False,
        ),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("answer_text_preview", sa.Text(), nullable=False),
        sa.Column("scores", sa.JSON(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("weakness_tags", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["interview_questions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_interview_answers_question_id",
        "interview_answers",
        ["question_id"],
    )
    op.create_index(
        "ix_interview_answers_user_id",
        "interview_answers",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_interview_answers_user_id", table_name="interview_answers")
    op.drop_index("ix_interview_answers_question_id", table_name="interview_answers")
    op.drop_table("interview_answers")
    op.drop_index("ix_interview_questions_difficulty", table_name="interview_questions")
    op.drop_index("ix_interview_questions_question_type", table_name="interview_questions")
    op.drop_index(
        "ix_interview_questions_project_rewrite_id",
        table_name="interview_questions",
    )
    op.drop_index("ix_interview_questions_project_id", table_name="interview_questions")
    op.drop_index(
        "ix_interview_questions_resume_version_id",
        table_name="interview_questions",
    )
    op.drop_index("ix_interview_questions_jd_id", table_name="interview_questions")
    op.drop_index("ix_interview_questions_user_id", table_name="interview_questions")
    op.drop_table("interview_questions")
