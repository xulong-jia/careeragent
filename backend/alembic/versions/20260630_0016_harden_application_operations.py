"""harden application operations

Revision ID: 20260630_0016
Revises: 20260630_0015
Create Date: 2026-06-30
"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "20260630_0016"
down_revision: Union[str, None] = "20260630_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("applications") as batch_op:
        batch_op.add_column(sa.Column("source_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("location", sa.String(length=160), nullable=True))
        batch_op.add_column(
            sa.Column(
                "priority",
                sa.String(length=40),
                server_default="medium",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "interview_question_ids",
                sa.JSON(),
                server_default=sa.text("'[]'"),
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("last_contact_date", sa.Date(), nullable=True))
        batch_op.create_index("ix_applications_location", ["location"])
        batch_op.create_index("ix_applications_priority", ["priority"])

    op.create_table(
        "application_status_history",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("from_status", sa.String(length=40), nullable=True),
        sa.Column("to_status", sa.String(length=40), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.String(length=240), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_application_status_history_application_id",
        "application_status_history",
        ["application_id"],
    )
    op.create_index(
        "ix_application_status_history_to_status",
        "application_status_history",
        ["to_status"],
    )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, status, created_at FROM applications")
    ).mappings()
    for row in rows:
        created_at = row["created_at"]
        connection.execute(
            sa.text(
                """
                INSERT INTO application_status_history
                    (id, application_id, from_status, to_status, changed_at, reason, note)
                VALUES
                    (:id, :application_id, NULL, :to_status, :changed_at, :reason, :note)
                """
            ),
            {
                "id": f"app_hist_{uuid4().hex[:12]}",
                "application_id": row["id"],
                "to_status": row["status"],
                "changed_at": created_at,
                "reason": "migration",
                "note": "Backfilled initial status during v1.4 migration.",
            },
        )


def downgrade() -> None:
    op.drop_index(
        "ix_application_status_history_to_status",
        table_name="application_status_history",
    )
    op.drop_index(
        "ix_application_status_history_application_id",
        table_name="application_status_history",
    )
    op.drop_table("application_status_history")

    with op.batch_alter_table("applications") as batch_op:
        batch_op.drop_index("ix_applications_priority")
        batch_op.drop_index("ix_applications_location")
        batch_op.drop_column("last_contact_date")
        batch_op.drop_column("interview_question_ids")
        batch_op.drop_column("notes")
        batch_op.drop_column("priority")
        batch_op.drop_column("location")
        batch_op.drop_column("source_url")
