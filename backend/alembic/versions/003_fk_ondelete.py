"""add ondelete to foreign keys and make firmware_updates.user_public_id nullable

Revision ID: 003_fk_ondelete
Revises: 002_plugin_packages
Create Date: 2026-02-16 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "003_fk_ondelete"
down_revision = "002_plugin_packages"
branch_labels = None
depends_on = None


# (table, constraint_name, columns, ref_table.ref_col, ondelete)
_FK_CASCADE = [
    ("events", "fk_events_user_public_id", ["user_public_id"], "users.public_id", "CASCADE"),
    ("experiments", "fk_experiments_user_public_id", ["user_public_id"], "users.public_id", "CASCADE"),
    ("datapoints", "fk_datapoints_event_public_id", ["event_public_id"], "events.public_id", "CASCADE"),
    ("datapoints", "fk_datapoints_experiment_public_id", ["experiment_public_id"], "experiments.public_id", "SET NULL"),
    ("log_entries", "fk_log_entries_user_public_id", ["user_public_id"], "users.public_id", "CASCADE"),
    ("webhooks", "fk_webhooks_user_public_id", ["user_public_id"], "users.public_id", "CASCADE"),
    ("webhook_deliveries", "fk_webhook_deliveries_webhook_id", ["webhook_id"], "webhooks.id", "CASCADE"),
    ("rules", "fk_rules_event_public_id", ["event_public_id"], "events.public_id", "CASCADE"),
    ("rules", "fk_rules_user_public_id", ["user_public_id"], "users.public_id", "CASCADE"),
    ("firmware_updates", "fk_firmware_updates_user_public_id", ["user_public_id"], "users.public_id", "SET NULL"),
    ("dashboards", "fk_dashboards_user_public_id", ["user_public_id"], "users.public_id", "CASCADE"),
    ("dashboard_widgets", "fk_dashboard_widgets_dashboard_id", ["dashboard_id"], "dashboards.id", "CASCADE"),
    ("dashboard_widgets", "fk_dashboard_widgets_event_public_id", ["event_public_id"], "events.public_id", "SET NULL"),
    ("plugin_instances", "fk_plugin_instances_user_public_id", ["user_public_id"], "users.public_id", "CASCADE"),
    ("channel_mappings", "fk_channel_mappings_plugin_instance_id", ["plugin_instance_id"], "plugin_instances.id", "CASCADE"),
    ("channel_mappings", "fk_channel_mappings_event_public_id", ["event_public_id"], "events.public_id", "SET NULL"),
    ("plugin_packages", "fk_plugin_packages_user_public_id", ["user_public_id"], "users.public_id", "SET NULL"),
]


def _find_fk_name(conn, table: str, columns: list[str]) -> str | None:
    """Look up the actual FK constraint name from the database."""
    from sqlalchemy import inspect as sa_inspect

    inspector = sa_inspect(conn)
    for fk in inspector.get_foreign_keys(table):
        if fk["constrained_columns"] == columns:
            return fk["name"]
    return None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Make firmware_updates.user_public_id nullable
    op.alter_column("firmware_updates", "user_public_id", nullable=True)

    # 2. Re-create each FK with ondelete
    for table, new_name, columns, referent, ondelete in _FK_CASCADE:
        # Find existing FK name (auto-generated names vary by DB)
        existing_name = _find_fk_name(conn, table, columns)
        if existing_name:
            op.drop_constraint(existing_name, table, type_="foreignkey")
        op.create_foreign_key(new_name, table, referent.split(".")[0], columns, [referent.split(".")[1]], ondelete=ondelete)


def downgrade() -> None:
    conn = op.get_bind()

    # Reverse: drop named FKs, recreate without ondelete
    for table, new_name, columns, referent, _ondelete in reversed(_FK_CASCADE):
        existing_name = _find_fk_name(conn, table, columns)
        if existing_name:
            op.drop_constraint(existing_name, table, type_="foreignkey")
        # Re-create without ondelete
        op.create_foreign_key(None, table, referent.split(".")[0], columns, [referent.split(".")[1]])

    # Revert firmware_updates.user_public_id to NOT NULL
    op.alter_column("firmware_updates", "user_public_id", nullable=False)
