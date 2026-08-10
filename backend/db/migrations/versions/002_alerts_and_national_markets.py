"""Alerts, national markets, and listing lease-rate fields

Revision ID: 002
Revises: 001
Create Date: 2026-04-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- listings: add lease-rate fields ---
    op.add_column("listings", sa.Column("lease_rate_nnn", sa.Numeric(8, 2)))
    op.add_column("listings", sa.Column("is_new_construction", sa.Boolean, server_default="false"))
    op.add_column("listings", sa.Column("land_price_per_sqft", sa.Numeric(10, 2)))
    op.add_column("listings", sa.Column("metro", sa.String(60)))
    op.add_column("listings", sa.Column("state", sa.String(4)))
    op.create_index("idx_listings_metro", "listings", ["metro"])
    op.create_index("idx_listings_lease_rate", "listings", ["lease_rate_nnn"])

    # --- national_markets: metro-level vacancy & rent data from public sources ---
    op.create_table(
        "national_markets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("metro", sa.String(80), nullable=False),
        sa.Column("state", sa.String(4)),
        sa.Column("vacancy_rate", sa.Numeric(5, 3)),
        sa.Column("avg_asking_rent_nnn", sa.Numeric(8, 2)),
        sa.Column("avg_land_price_per_sqft", sa.Numeric(10, 2)),
        sa.Column("rent_yoy_pct", sa.Numeric(6, 3)),
        sa.Column("net_absorption_sqft", sa.Integer),
        sa.Column("under_construction_sqft", sa.Integer),
        sa.Column("market_type", sa.String(20)),  # 'emerging' | 'primary' | 'secondary'
        sa.Column("source", sa.String(40)),
        sa.Column("source_url", sa.Text),
        sa.Column("as_of_date", sa.Date),
        sa.Column("fetched_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("metro", "source", "as_of_date", name="uq_national_markets_metro_src_date"),
    )
    op.create_index("idx_national_markets_vacancy", "national_markets", ["vacancy_rate"])
    op.create_index("idx_national_markets_metro", "national_markets", ["metro"])

    # --- alert_subscribers: filter preferences for 2x/week market digests ---
    op.create_table(
        "alert_subscribers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(180)),
        sa.Column("phone", sa.String(30)),  # stored but unused until SMS enabled
        sa.Column("filters", JSONB, nullable=False, server_default="{}"),
        sa.Column("delivery", sa.String(20), server_default="'digest'"),  # digest | email | sms
        sa.Column("frequency", sa.String(20), server_default="'2x_weekly'"),
        sa.Column("active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_alert_subscribers_active", "alert_subscribers", ["active"])

    # --- market_digests: generated 2x/week per subscriber (or anonymous) ---
    op.create_table(
        "market_digests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("subscriber_id", sa.Integer, sa.ForeignKey("alert_subscribers.id", ondelete="CASCADE")),
        sa.Column("generated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("period_start", sa.Date),
        sa.Column("period_end", sa.Date),
        sa.Column("match_count", sa.Integer, server_default="0"),
        sa.Column("payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("delivered", sa.Boolean, server_default="false"),
        sa.Column("delivered_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_market_digests_subscriber", "market_digests", ["subscriber_id"])
    op.create_index("idx_market_digests_generated", "market_digests", ["generated_at"])


def downgrade() -> None:
    op.drop_table("market_digests")
    op.drop_table("alert_subscribers")
    op.drop_table("national_markets")
    op.drop_index("idx_listings_lease_rate", table_name="listings")
    op.drop_index("idx_listings_metro", table_name="listings")
    op.drop_column("listings", "state")
    op.drop_column("listings", "metro")
    op.drop_column("listings", "land_price_per_sqft")
    op.drop_column("listings", "is_new_construction")
    op.drop_column("listings", "lease_rate_nnn")
