"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


ENUMS = {
    "user_role": ("user", "admin"),
    "upload_status": ("received", "queued", "processing", "completed", "failed"),
    "media_status": ("pending", "processing", "completed", "failed"),
    "job_status": ("queued", "running", "succeeded", "failed", "retrying", "dead"),
    "worker_status": ("idle", "busy", "offline"),
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


def _now() -> sa.text:
    return sa.text("now()")


def upgrade() -> None:
    _create_enums()

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("role", _pg_enum("user_role"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "uploads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("public_id", sa.String(16), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("optimized_filename", sa.String(512), nullable=True),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("extension", sa.String(16), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("storage_location", sa.String(1024), nullable=False),
        sa.Column("status", _pg_enum("upload_status"), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("download_count", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_uploads_public_id", "uploads", ["public_id"], unique=True)
    op.create_index("ix_uploads_user_id", "uploads", ["user_id"])

    op.create_table(
        "media_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("stored_filename", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("extension", sa.String(16), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("storage_location", sa.String(1024), nullable=False),
        sa.Column("status", _pg_enum("media_status"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("upload_id", "seq", name="uq_media_files_upload_seq"),
    )
    op.create_index("ix_media_files_upload_id", "media_files", ["upload_id"])

    op.create_table(
        "processed_media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("media_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("processed_filename", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("extension", sa.String(16), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("storage_location", sa.String(1024), nullable=False),
        sa.Column("status", _pg_enum("media_status"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.ForeignKeyConstraint(["media_file_id"], ["media_files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_processed_media_upload_id", "processed_media", ["upload_id"])

    op.create_table(
        "settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("value", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("group", sa.String(64), nullable=False),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("is_secret", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
    )
    op.create_index("ix_settings_key", "settings", ["key"], unique=True)

    op.create_table(
        "watermarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("text", sa.String(255), nullable=True),
        sa.Column("image_url", sa.String(512), nullable=True),
        sa.Column("position", sa.String(32), nullable=False),
        sa.Column("opacity", sa.Float(), nullable=False),
        sa.Column("size_percent", sa.Float(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
    )
    op.create_index("ix_watermarks_name", "watermarks", ["name"], unique=True)

    op.create_table(
        "ad_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("base_url", sa.String(512), nullable=True),
        sa.Column("api_key", sa.String(512), nullable=True),
        sa.Column("click_through_url", sa.String(512), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
    )
    op.create_index("ix_ad_providers_name", "ad_providers", ["name"], unique=True)

    op.create_table(
        "traffic_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("country", sa.String(64), nullable=True),
        sa.Column("device", sa.String(64), nullable=True),
        sa.Column("browser", sa.String(64), nullable=True),
        sa.Column("page_url", sa.String(512), nullable=True),
        sa.Column("referrer", sa.String(512), nullable=True),
        sa.Column("events_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_traffic_stats_stat_date", "traffic_stats", ["stat_date"])

    op.create_table(
        "analytics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_analytics_event_type", "analytics", ["event_type"])
    op.create_index("ix_analytics_upload_id", "analytics", ["upload_id"])

    op.create_table(
        "whatsapp_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("phone_number_id", sa.String(128), nullable=True),
        sa.Column("access_token", sa.String(512), nullable=True),
        sa.Column("webhook_verify_token", sa.String(255), nullable=True),
        sa.Column("webhook_secret", sa.String(255), nullable=True),
        sa.Column("api_version", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
    )
    op.create_index("ix_whatsapp_settings_name", "whatsapp_settings", ["name"], unique=True)

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("key_hash", sa.String(128), nullable=False),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("scopes", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.String(32), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(128), nullable=True),
        sa.Column("details", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    op.create_table(
        "system_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("logger_name", sa.String(128), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("context", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
    )
    op.create_index("ix_system_logs_level", "system_logs", ["level"])

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(128), nullable=False),
        sa.Column("status", _pg_enum("job_status"), nullable=False),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("celery_task_id", sa.String(128), nullable=True),
        sa.Column("args", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("result", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=True),
        sa.Column("retries", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("traceback", sa.Text(), nullable=True),
        sa.Column("worker_id", sa.String(128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_jobs_job_type", "jobs", ["job_type"])
    op.create_index("ix_jobs_upload_id", "jobs", ["upload_id"])
    op.create_index("ix_jobs_celery_task_id", "jobs", ["celery_task_id"], unique=True)

    op.create_table(
        "workers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("hostname", sa.String(255), nullable=True),
        sa.Column("status", _pg_enum("worker_status"), nullable=False),
        sa.Column("current_job_id", sa.String(128), nullable=True),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_now()),
    )
    op.create_index("ix_workers_name", "workers", ["name"], unique=True)


def downgrade() -> None:
    op.drop_table("workers")
    op.drop_table("jobs")
    op.drop_table("system_logs")
    op.drop_table("audit_logs")
    op.drop_table("api_keys")
    op.drop_table("whatsapp_settings")
    op.drop_table("analytics")
    op.drop_table("traffic_stats")
    op.drop_table("ad_providers")
    op.drop_table("watermarks")
    op.drop_table("settings")
    op.drop_table("processed_media")
    op.drop_table("media_files")
    op.drop_table("uploads")
    op.drop_table("users")
    _drop_enums()
