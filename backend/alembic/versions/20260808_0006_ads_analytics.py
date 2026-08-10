"""ads, placements, ad events and analytics aggregation

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-08 00:00:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def _add_enum_values() -> None:
    """Best-effort backfill for DBs that created a ``permission`` enum type.

    HD Guru stores permissions as application-side string values (the
    ``permission`` values live in ``app/models/enums.py`` and are persisted as
    plain strings), so a ``permission`` Postgres enum type does not exist on a
    fresh database. Only extend it when an existing database actually created
    the type — otherwise ``alembic upgrade head`` would fail on Postgres with
    ``type "permission" does not exist``.
    """
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    exists = bind.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = 'permission'")
    ).first()
    if not exists:
        return
    for value in ("ads.view", "ads.manage", "analytics.view"):
        op.execute(
            sa.text(
                "DO $$ BEGIN "
                f"ALTER TYPE permission ADD VALUE IF NOT EXISTS '{value}'; "
                "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
            )
        )


def upgrade() -> None:
    _add_enum_values()

    # --- ad_providers: extend with integration fields -----------------------
    op.add_column(
        "ad_providers",
        sa.Column(
            "provider_type",
            sa.String(32),
            server_default="script",
            nullable=False,
        ),
    )
    op.add_column("ad_providers", sa.Column("publisher_id", sa.String(255), nullable=True))
    op.add_column("ad_providers", sa.Column("zone_id", sa.String(255), nullable=True))
    op.add_column("ad_providers", sa.Column("site_id", sa.String(255), nullable=True))
    op.add_column(
        "ad_providers",
        sa.Column("placement_config", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
    )
    op.add_column("ad_providers", sa.Column("custom_script", sa.Text(), nullable=True))

    # --- ad_placements + placement/provider association ----------------------
    op.create_table(
        "ad_placements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("label", sa.String(128), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column(
            "responsive",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "behavior",
            sa.String(32),
            server_default="lazy",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ad_placements_name", "ad_placements", ["name"], unique=True)

    op.create_table(
        "ad_placement_providers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("placement_id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "frequency",
            sa.String(32),
            server_default="every_page",
            nullable=False,
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("config", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("placement_id", "provider_id", name="uq_ad_placement_provider"),
    )
    op.create_index(
        "ix_ad_placement_providers_placement_id",
        "ad_placement_providers",
        ["placement_id"],
    )
    op.create_index(
        "ix_ad_placement_providers_provider_id",
        "ad_placement_providers",
        ["provider_id"],
    )

    # --- ad_events ----------------------------------------------------------
    op.create_table(
        "ad_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=True),
        sa.Column("placement_id", sa.Uuid(), nullable=True),
        sa.Column("provider_name", sa.String(128), nullable=True),
        sa.Column("placement_name", sa.String(64), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("page", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["provider_id"], ["ad_providers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["placement_id"], ["ad_placements.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ad_events_event_type", "ad_events", ["event_type"])
    op.create_index("ix_ad_events_provider_id", "ad_events", ["provider_id"])
    op.create_index("ix_ad_events_placement_id", "ad_events", ["placement_id"])
    op.create_index("ix_ad_events_placement_name", "ad_events", ["placement_name"])
    op.create_index("ix_ad_events_session_id", "ad_events", ["session_id"])
    op.create_index("ix_ad_events_created_at", "ad_events", ["created_at"])

    # --- analytics: coarse privacy dimensions -------------------------------
    op.add_column("analytics", sa.Column("session_id", sa.String(64), nullable=True))
    op.add_column("analytics", sa.Column("page", sa.String(128), nullable=True))
    op.add_column("analytics", sa.Column("device", sa.String(32), nullable=True))
    op.add_column("analytics", sa.Column("browser", sa.String(32), nullable=True))
    op.add_column("analytics", sa.Column("os", sa.String(32), nullable=True))
    op.add_column("analytics", sa.Column("country", sa.String(8), nullable=True))
    op.add_column(
        "analytics",
        sa.Column("referrer_category", sa.String(32), nullable=True),
    )
    op.create_index("ix_analytics_session_id", "analytics", ["session_id"])
    op.create_index("ix_analytics_page", "analytics", ["page"])
    op.create_index("ix_analytics_created_at", "analytics", ["created_at"])

    # --- traffic_stats: aggregate counters + unique dimension index ----------
    op.add_column("traffic_stats", sa.Column("os", sa.String(64), nullable=True))
    for col in (
        "page_views",
        "sessions",
        "uploads",
        "uploads_completed",
        "processing_completed",
        "get_hd_clicks",
        "whatsapp_opens",
        "whatsapp_requests",
        "media_deliveries",
        "errors",
        "ad_impressions",
        "ad_clicks",
        "ad_load_failures",
    ):
        op.add_column(
            "traffic_stats",
            sa.Column(col, sa.Integer(), server_default="0", nullable=False),
        )
    # Composite unique index over the daily aggregate dimensions (keeps the
    # upsert deterministic without a full table rebuild on SQLite).
    op.create_index(
        "uq_traffic_stats_dims",
        "traffic_stats",
        [
            "stat_date",
            "page_url",
            "device",
            "browser",
            "os",
            "country",
            "referrer",
        ],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_traffic_stats_dims", table_name="traffic_stats")
    for col in (
        "ad_load_failures",
        "ad_clicks",
        "ad_impressions",
        "errors",
        "media_deliveries",
        "whatsapp_requests",
        "whatsapp_opens",
        "get_hd_clicks",
        "processing_completed",
        "uploads_completed",
        "uploads",
        "sessions",
        "page_views",
    ):
        op.drop_column("traffic_stats", col)
    op.drop_column("traffic_stats", "os")

    op.drop_index("ix_analytics_created_at", table_name="analytics")
    op.drop_index("ix_analytics_page", table_name="analytics")
    op.drop_index("ix_analytics_session_id", table_name="analytics")
    op.drop_column("analytics", "referrer_category")
    op.drop_column("analytics", "country")
    op.drop_column("analytics", "os")
    op.drop_column("analytics", "browser")
    op.drop_column("analytics", "device")
    op.drop_column("analytics", "page")
    op.drop_column("analytics", "session_id")

    op.drop_table("ad_events")
    op.drop_index("ix_ad_placement_providers_provider_id", table_name="ad_placement_providers")
    op.drop_index("ix_ad_placement_providers_placement_id", table_name="ad_placement_providers")
    op.drop_table("ad_placement_providers")
    op.drop_index("ix_ad_placements_name", table_name="ad_placements")
    op.drop_table("ad_placements")

    op.drop_column("ad_providers", "custom_script")
    op.drop_column("ad_providers", "placement_config")
    op.drop_column("ad_providers", "site_id")
    op.drop_column("ad_providers", "zone_id")
    op.drop_column("ad_providers", "publisher_id")
    op.drop_column("ad_providers", "provider_type")
