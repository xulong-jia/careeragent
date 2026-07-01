"""add auth sessions

Revision ID: 20260701_0024
Revises: 20260701_0023
Create Date: 2026-07-01 00:24:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260701_0024"
down_revision = "20260701_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("token_jti", sa.String(length=64), nullable=False),
        sa.Column("device_label", sa.String(length=160), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoke_reason", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("session_id"),
        sa.UniqueConstraint("token_jti", name="uq_auth_sessions_token_jti"),
    )
    op.create_index("ix_auth_sessions_token_jti", "auth_sessions", ["token_jti"])
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_workspace_id", "auth_sessions", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_workspace_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_token_jti", table_name="auth_sessions")
    op.drop_table("auth_sessions")
