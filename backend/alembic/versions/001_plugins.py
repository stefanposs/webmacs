"""add plugin_instances and channel_mappings tables

Revision ID: 001_plugins
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "001_plugins"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── plugin_instances ─────────────────────────────────────────────────
    op.create_table(
        "plugin_instances",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(100), nullable=False),
        sa.Column("plugin_id", sa.String(100), nullable=False),
        sa.Column("instance_name", sa.String(255), nullable=False),
        sa.Column("demo_mode", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("inactive", "connected", "error", "demo", name="pluginstatus"),
            server_default="inactive",
            nullable=False,
        ),
        sa.Column("config_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_on", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_on", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_public_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("instance_name"),
        sa.ForeignKeyConstraint(["user_public_id"], ["users.public_id"]),
    )
    op.create_index("ix_plugin_instances_plugin_id", "plugin_instances", ["plugin_id"])
    op.create_index("ix_plugin_instances_user_public_id", "plugin_instances", ["user_public_id"])

    # ── channel_mappings ─────────────────────────────────────────────────
    op.create_table(
        "channel_mappings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(100), nullable=False),
        sa.Column("plugin_instance_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.String(100), nullable=False),
        sa.Column("channel_name", sa.String(255), nullable=False),
        sa.Column(
            "direction",
            sa.Enum("input", "output", "bidirectional", name="channeldirection"),
            nullable=False,
        ),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("event_public_id", sa.String(), nullable=True),
        sa.Column("created_on", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.ForeignKeyConstraint(["plugin_instance_id"], ["plugin_instances.id"]),
        sa.ForeignKeyConstraint(["event_public_id"], ["events.public_id"]),
    )
    op.create_index("ix_channel_mappings_plugin_instance_id", "channel_mappings", ["plugin_instance_id"])
    op.create_index("ix_channel_mappings_event_public_id", "channel_mappings", ["event_public_id"])
    op.create_index(
        "ix_channel_mappings_plugin_channel",
        "channel_mappings",
        ["plugin_instance_id", "channel_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("channel_mappings")
    op.drop_table("plugin_instances")
    op.execute("DROP TYPE IF EXISTS channeldirection")
    op.execute("DROP TYPE IF EXISTS pluginstatus")
