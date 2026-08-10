"""media pipeline: public ids, pipeline stages, processed media metadata

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-08 00:00:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# New MediaStatus values added by the Phase 3 pipeline. The existing values
# (pending, processing, completed, failed) are kept for backward compatibility.
_NEW_MEDIA_STATUS_VALUES = (
    "queued",
    "analyzing",
    "enhancing",
    "watermarking",
    "compressing",
    "storing",
    "expired",
)

_JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _add_enum_values(bind) -> None:
    if bind.dialect.name != "postgresql":
        return
    for value in _NEW_MEDIA_STATUS_VALUES:
        op.execute(
            sa.text(
                "DO $$ BEGIN "
                f"ALTER TYPE media_status ADD VALUE IF NOT EXISTS '{value}'; "
                "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
            )
        )


def _backfill_media_public_ids(bind) -> None:
    from app.utils.ids import generate_public_id

    rows = bind.execute(
        sa.text("SELECT id FROM media_files WHERE public_id IS NULL")
    ).fetchall()
    for (row_id,) in rows:
        bind.execute(
            sa.text("UPDATE media_files SET public_id = :p WHERE id = :i"),
            {"p": generate_public_id(), "i": str(row_id)},
        )


def upgrade() -> None:
    bind = op.get_bind()
    _add_enum_values(bind)

    op.add_column("media_files", sa.Column("public_id", sa.String(16), nullable=True))
    op.add_column("media_files", sa.Column("error", sa.Text(), nullable=True))
    _backfill_media_public_ids(bind)
    with op.batch_alter_table("media_files") as batch:
        batch.alter_column("public_id", existing_type=sa.String(16), nullable=False)
        batch.create_index("ix_media_files_public_id", ["public_id"], unique=True)

    op.add_column(
        "processed_media",
        sa.Column("thumbnail_location", sa.String(1024), nullable=True),
    )
    op.add_column(
        "processed_media",
        sa.Column("watermark_ref", _JSON_TYPE, nullable=True),
    )
    op.add_column(
        "processed_media",
        sa.Column(
            "download_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "processed_media",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("processed_media", "completed_at")
    op.drop_column("processed_media", "download_count")
    op.drop_column("processed_media", "watermark_ref")
    op.drop_column("processed_media", "thumbnail_location")

    with op.batch_alter_table("media_files") as batch:
        batch.drop_index("ix_media_files_public_id")
        batch.drop_column("public_id")
        batch.drop_column("error")

    # Enum values are intentionally not removed on downgrade; removing enum
    # values on Postgres requires recreating the type.
