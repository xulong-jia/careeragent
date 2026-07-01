"""add token revoke foundation

Revision ID: 20260701_0023
Revises: 20260701_0022
Create Date: 2026-07-01 00:23:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260701_0023"
down_revision = "20260701_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "revoked_tokens",
        sa.Column("token_jti", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.String(length=80), nullable=False, server_default="logout"),
        sa.PrimaryKeyConstraint("token_jti"),
    )
    op.create_index("ix_revoked_tokens_user_id", "revoked_tokens", ["user_id"])
    op.create_index("ix_revoked_tokens_workspace_id", "revoked_tokens", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_revoked_tokens_workspace_id", table_name="revoked_tokens")
    op.drop_index("ix_revoked_tokens_user_id", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
