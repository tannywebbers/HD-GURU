"""object storage: storage provider + object keys for media

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-08 00:00:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column(
        "media_files",
        sa.Column("storage_provider", sa.String(16), nullable=True),
    )
    op.add_column(
        "media_files",
        sa.Column("original_object_key", sa.String(1024), nullable=True),
    )

    op.add_column(
        "processed_media",
        sa.Column("storage_provider", sa.String(16), nullable=True),
    )
    op.add_column(
        "processed_media",
        sa.Column("processed_object_key", sa.String(1024), nullable=True),
    )
    op.add_column(
        "processed_media",
        sa.Column("thumbnail_object_key", sa.String(1024), nullable=True),
    )

    # Existing rows predate object storage; they live on the local driver.
    bind.execute(
        sa.text("UPDATE media_files SET storage_provider = 'local' WHERE storage_provider IS NULL")
    )
    bind.execute(
        sa.text(
            "UPDATE media_files SET original_object_key = storage_location "
            "WHERE original_object_key IS NULL AND storage_location IS NOT NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE processed_media SET storage_provider = 'local' "
            "WHERE storage_provider IS NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE processed_media SET processed_object_key = storage_location "
            "WHERE processed_object_key IS NULL AND storage_location IS NOT NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE processed_media SET thumbnail_object_key = thumbnail_location "
            "WHERE thumbnail_object_key IS NULL AND thumbnail_location IS NOT NULL"
        )
    )

    with op.batch_alter_table("media_files") as batch:
        batch.alter_column(
            "storage_provider",
            existing_type=sa.String(16),
            nullable=False,
            existing_server_default=sa.text("'local'"),
        )
        batch.create_index(
            "ix_media_files_original_object_key", ["original_object_key"]
        )
    with op.batch_alter_table("processed_media") as batch:
        batch.alter_column(
            "storage_provider",
            existing_type=sa.String(16),
            nullable=False,
            existing_server_default=sa.text("'local'"),
        )
        batch.create_index(
            "ix_processed_media_processed_object_key", ["processed_object_key"]
        )
        batch.create_index(
            "ix_processed_media_thumbnail_object_key", ["thumbnail_object_key"]
        )


def downgrade() -> None:
    with op.batch_alter_table("processed_media") as batch:
        batch.drop_index("ix_processed_media_thumbnail_object_key")
        batch.drop_index("ix_processed_media_processed_object_key")
        batch.drop_column("thumbnail_object_key")
        batch.drop_column("processed_object_key")
        batch.drop_column("storage_provider")
    with op.batch_alter_table("media_files") as batch:
        batch.drop_index("ix_media_files_original_object_key")
        batch.drop_column("original_object_key")
        batch.drop_column("storage_provider")
