"""add SSO / OIDC columns to users table

Revision ID: 005_oidc_sso
Revises: 004_rbac_api_tokens
Create Date: 2026-02-17 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "005_oidc_sso"
down_revision = "004_rbac_api_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("sso_provider", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("sso_subject_id", sa.String(255), nullable=True))
    # Composite index for fast SSO lookups
    op.create_index("ix_users_sso_lookup", "users", ["sso_provider", "sso_subject_id"])
    # Partial unique constraint — prevent duplicate SSO identities
    op.create_unique_constraint("uq_users_sso_identity", "users", ["sso_provider", "sso_subject_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_sso_identity", "users", type_="unique")
    op.drop_index("ix_users_sso_lookup", table_name="users")
    op.drop_column("users", "sso_subject_id")
    op.drop_column("users", "sso_provider")
