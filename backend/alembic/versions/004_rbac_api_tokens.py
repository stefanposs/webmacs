"""add user roles and api_tokens table

Revision ID: 004_rbac_api_tokens
Revises: 003_fk_ondelete
Create Date: 2026-02-17 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004_rbac_api_tokens"
down_revision = "003_fk_ondelete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- 1. Add 'role' column to users (default='viewer') ---
    op.add_column("users", sa.Column("role", sa.String(20), nullable=True))

    # Migrate existing data: admin=True → 'admin', else → 'viewer'
    op.execute("UPDATE users SET role = CASE WHEN admin = TRUE THEN 'admin' ELSE 'viewer' END")

    # Make column non-nullable now that data is populated
    op.alter_column("users", "role", nullable=False, server_default="viewer")

    # Drop the old 'admin' column
    op.drop_column("users", "admin")

    # --- 2. Create api_tokens table ---
    op.create_table(
        "api_tokens",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    # Drop api_tokens table
    op.drop_table("api_tokens")

    # Re-add 'admin' column
    op.add_column("users", sa.Column("admin", sa.Boolean, nullable=True, server_default=sa.text("FALSE")))

    # Migrate data back: role='admin' → admin=True
    op.execute("UPDATE users SET admin = (role = 'admin')")

    op.alter_column("users", "admin", nullable=False)

    # Drop role column
    op.drop_column("users", "role")
