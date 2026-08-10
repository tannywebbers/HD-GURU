"""admin dashboard: roles, delivery counters, watermark margin

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-08 00:00:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_NEW_USER_ROLE_VALUES = (
    "viewer",
    "operator",
    "super_admin",
)


def _add_enum_values() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for value in _NEW_USER_ROLE_VALUES:
        op.execute(
            sa.text(
                "DO $$ BEGIN "
                f"ALTER TYPE user_role ADD VALUE IF NOT EXISTS '{value}'; "
                "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
            )
        )


def upgrade() -> None:
    _add_enum_values()

    op.add_column(
        "uploads",
        sa.Column(
            "whatsapp_delivery_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "media_files",
        sa.Column(
            "download_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "media_files",
        sa.Column(
            "whatsapp_delivery_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "watermarks",
        sa.Column("margin", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("watermarks", "margin")
    op.drop_column("media_files", "whatsapp_delivery_count")
    op.drop_column("media_files", "download_count")
    op.drop_column("uploads", "whatsapp_delivery_count")
