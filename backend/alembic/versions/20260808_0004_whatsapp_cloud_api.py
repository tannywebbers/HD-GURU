"""whatsapp cloud api: contacts, messages, statuses, webhook events

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-08 00:00:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


ENUMS = {
    "whatsapp_message_direction": ("inbound", "outbound"),
    "whatsapp_message_status": ("received", "processing", "sent", "failed", "ignored"),
    "whatsapp_delivery_status": ("sent", "delivered", "read", "failed"),
    "whatsapp_event_status": ("received", "processed", "failed", "ignored"),
}


def _create_enums() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for name, values in ENUMS.items():
        values_sql = ", ".join(f"'{v}'" for v in values)
        op.execute(
            "DO $$ BEGIN "
            f"CREATE TYPE {name} AS ENUM ({values_sql}); "
            "EXCEPTION WHEN duplicate_object THEN null; END $$;"
        )


def _drop_enums() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for name in ENUMS:
        op.execute(f"DROP TYPE IF EXISTS {name}")


def _pg_enum(name: str):
    return sa.Enum(*ENUMS[name], name=name, create_type=False)


def _json() -> sa.types.TypeEngine:
    return postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def _now() -> sa.text:
    return sa.text("now()")


def upgrade() -> None:
    _create_enums()

    op.add_column(
        "whatsapp_settings",
        sa.Column("phone_number", sa.String(32), nullable=True),
    )
    op.add_column(
        "whatsapp_settings",
        sa.Column("business_account_id", sa.String(128), nullable=True),
    )
    op.add_column(
        "whatsapp_settings",
        sa.Column("graph_api_base_url", sa.String(255), nullable=True),
    )

    op.create_table(
        "whatsapp_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("wa_id", sa.String(64), nullable=False),
        sa.Column("phone_number", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("profile", _json(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
    )
    op.create_index("ix_whatsapp_contacts_wa_id", "whatsapp_contacts", ["wa_id"], unique=True)
    op.create_index("ix_whatsapp_contacts_phone_number", "whatsapp_contacts", ["phone_number"])

    op.create_table(
        "whatsapp_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("meta_message_id", sa.String(128), nullable=False),
        sa.Column("direction", _pg_enum("whatsapp_message_direction"), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("message_type", sa.String(32), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("media_public_id", sa.String(16), nullable=True),
        sa.Column("status", _pg_enum("whatsapp_message_status"), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", _json(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.ForeignKeyConstraint(["contact_id"], ["whatsapp_contacts.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_whatsapp_messages_meta_message_id", "whatsapp_messages", ["meta_message_id"], unique=True)
    op.create_index("ix_whatsapp_messages_contact_id", "whatsapp_messages", ["contact_id"])
    op.create_index("ix_whatsapp_messages_media_public_id", "whatsapp_messages", ["media_public_id"])
    op.create_index("ix_whatsapp_messages_status", "whatsapp_messages", ["status"])

    op.create_table(
        "whatsapp_message_statuses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("meta_message_id", sa.String(128), nullable=False),
        sa.Column("status", _pg_enum("whatsapp_delivery_status"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", _json(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.ForeignKeyConstraint(["message_id"], ["whatsapp_messages.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_whatsapp_message_statuses_message_id", "whatsapp_message_statuses", ["message_id"])
    op.create_index("ix_whatsapp_message_statuses_meta_message_id", "whatsapp_message_statuses", ["meta_message_id"])
    op.create_index("ix_whatsapp_message_statuses_status", "whatsapp_message_statuses", ["status"])

    op.create_table(
        "whatsapp_webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("object", sa.String(128), nullable=True),
        sa.Column("entry_id", sa.String(128), nullable=True),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("status", _pg_enum("whatsapp_event_status"), nullable=False),
        sa.Column("payload", _json(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
    )
    op.create_index("ix_whatsapp_webhook_events_status", "whatsapp_webhook_events", ["status"])
    op.create_index("ix_whatsapp_webhook_events_event_type", "whatsapp_webhook_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("whatsapp_webhook_events")
    op.drop_table("whatsapp_message_statuses")
    op.drop_table("whatsapp_messages")
    op.drop_table("whatsapp_contacts")

    with op.batch_alter_table("whatsapp_settings") as batch:
        batch.drop_column("graph_api_base_url")
        batch.drop_column("business_account_id")
        batch.drop_column("phone_number")

    _drop_enums()
