"""add plugin_packages table

Revision ID: 002_plugin_packages
Revises: 001_plugins
Create Date: 2026-02-14 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "002_plugin_packages"
down_revision = "001_plugins"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plugin_packages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(100), nullable=False),
        sa.Column("package_name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column(
            "source",
            sa.Enum("bundled", "uploaded", name="pluginsource"),
            nullable=False,
        ),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_hash_sha256", sa.String(64), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("plugin_ids", sa.Text(), nullable=False, server_default="[]"),
        sa.Column(
            "installed_on",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("user_public_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("package_name"),
        sa.ForeignKeyConstraint(["user_public_id"], ["users.public_id"]),
    )
    op.create_index(
        "ix_plugin_packages_user_public_id",
        "plugin_packages",
        ["user_public_id"],
    )


def downgrade() -> None:
    op.drop_table("plugin_packages")
    op.execute("DROP TYPE IF EXISTS pluginsource")
