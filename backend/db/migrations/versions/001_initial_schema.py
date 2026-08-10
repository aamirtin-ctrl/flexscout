"""Initial schema — all Phase 1 tables

Revision ID: 001
Revises:
Create Date: 2026-04-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
import geoalchemy2

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable PostGIS
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # --- parcels ---
    op.create_table(
        "parcels",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("apn", sa.String(50), nullable=False),
        sa.Column("county", sa.String(20), nullable=False),
        sa.Column("address", sa.Text),
        sa.Column("lat", sa.Numeric(10, 7)),
        sa.Column("lng", sa.Numeric(10, 7)),
        sa.Column("geom", geoalchemy2.Geometry("POINT", srid=4326), nullable=True),
        sa.Column("acreage", sa.Numeric(10, 3)),
        sa.Column("zoning_code", sa.String(20)),
        sa.Column("zoning_desc", sa.Text),
        sa.Column("land_use_code", sa.String(10)),
        sa.Column("land_value", sa.Integer),
        sa.Column("imprv_value", sa.Integer),
        sa.Column("owner_name", sa.Text),
        sa.Column("owner_since", sa.Date),
        sa.Column("is_vacant", sa.Boolean, server_default="false"),
        sa.Column("is_delinquent", sa.Boolean, server_default="false"),
        sa.Column("delinquency_amt", sa.Integer),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("apn", "county", name="uq_parcels_apn_county"),
    )
    op.create_index("idx_parcels_geom", "parcels", ["geom"], postgresql_using="gist")
    op.create_index("idx_parcels_county", "parcels", ["county"])
    op.create_index("idx_parcels_zoning", "parcels", ["zoning_code"])

    # --- buildings ---
    op.create_table(
        "buildings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("parcel_id", sa.Integer, sa.ForeignKey("parcels.id")),
        sa.Column("apn", sa.String(50)),
        sa.Column("county", sa.String(20)),
        sa.Column("address", sa.Text),
        sa.Column("lat", sa.Numeric(10, 7)),
        sa.Column("lng", sa.Numeric(10, 7)),
        sa.Column("geom", geoalchemy2.Geometry("POINT", srid=4326), nullable=True),
        sa.Column("sqft", sa.Integer),
        sa.Column("year_built", sa.Integer),
        sa.Column("clear_height_ft", sa.Integer),
        sa.Column("dock_doors", sa.Integer),
        sa.Column("drive_in_doors", sa.Integer),
        sa.Column("office_pct", sa.Numeric(5, 2)),
        sa.Column("last_sale_date", sa.Date),
        sa.Column("last_sale_price", sa.Integer),
        sa.Column("source", sa.String(30)),
        sa.Column("source_id", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_buildings_geom", "buildings", ["geom"], postgresql_using="gist")

    # --- transactions ---
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("apn", sa.String(50)),
        sa.Column("county", sa.String(20)),
        sa.Column("sale_date", sa.Date),
        sa.Column("sale_price", sa.Integer),
        sa.Column("price_per_sqft", sa.Numeric(10, 2)),
        sa.Column("grantor", sa.Text),
        sa.Column("grantee", sa.Text),
        sa.Column("instrument_type", sa.String(10)),
        sa.Column("doc_number", sa.String(50)),
        sa.Column("sqft", sa.Integer),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("doc_number", "county", name="uq_transactions_doc_county"),
    )
    op.create_index("idx_transactions_apn", "transactions", ["apn", "county"])
    op.create_index("idx_transactions_date", "transactions", ["sale_date"])

    # --- listings ---
    op.create_table(
        "listings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source", sa.String(20)),
        sa.Column("source_id", sa.String(100)),
        sa.Column("address", sa.Text),
        sa.Column("lat", sa.Numeric(10, 7)),
        sa.Column("lng", sa.Numeric(10, 7)),
        sa.Column("geom", geoalchemy2.Geometry("POINT", srid=4326), nullable=True),
        sa.Column("list_price", sa.Integer),
        sa.Column("price_per_sqft", sa.Numeric(10, 2)),
        sa.Column("sqft", sa.Integer),
        sa.Column("property_type", sa.String(30)),
        sa.Column("listing_date", sa.Date),
        sa.Column("days_on_market", sa.Integer),
        sa.Column("status", sa.String(20)),
        sa.Column("year_built", sa.Integer),
        sa.Column("clear_height_ft", sa.Integer),
        sa.Column("dock_doors", sa.Integer),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("source", "source_id", name="uq_listings_source"),
    )

    # --- deals ---
    op.create_table(
        "deals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("deal_type", sa.String(10), nullable=False),
        sa.Column("parcel_id", sa.Integer, sa.ForeignKey("parcels.id")),
        sa.Column("building_id", sa.Integer, sa.ForeignKey("buildings.id")),
        sa.Column("score", sa.Integer),
        sa.Column("tier", sa.String(5)),
        sa.Column("narrative", sa.Text),
        sa.Column("risk_flags", ARRAY(sa.Text), server_default="{}"),
        sa.Column("upside_flags", ARRAY(sa.Text), server_default="{}"),
        sa.Column("rec_action", sa.String(30)),
        sa.Column("status", sa.String(20), server_default="'new'"),
        sa.Column("assigned_to", sa.String(100)),
        sa.Column("scored_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_deals_score", "deals", [sa.text("score DESC")])
    op.create_index("idx_deals_status", "deals", ["status"])
    op.create_index("idx_deals_type", "deals", ["deal_type"])

    # --- comps ---
    op.create_table(
        "comps",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("subject_parcel_id", sa.Integer, sa.ForeignKey("parcels.id")),
        sa.Column("comp_parcel_id", sa.Integer, sa.ForeignKey("parcels.id")),
        sa.Column("distance_miles", sa.Numeric(6, 3)),
        sa.Column("sale_date", sa.Date),
        sa.Column("sale_price", sa.Integer),
        sa.Column("price_per_sqft", sa.Numeric(10, 2)),
        sa.Column("price_per_acre", sa.Integer),
        sa.Column("sqft", sa.Integer),
        sa.Column("acreage", sa.Numeric(10, 3)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # --- deal_notes ---
    op.create_table(
        "deal_notes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("deal_id", sa.Integer, sa.ForeignKey("deals.id")),
        sa.Column("note", sa.Text, nullable=False),
        sa.Column("author", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # --- submarket_stats ---
    op.create_table(
        "submarket_stats",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("submarket_name", sa.String(100)),
        sa.Column("as_of_date", sa.Date),
        sa.Column("vacancy_rate", sa.Numeric(5, 3)),
        sa.Column("avg_asking_rent_nnn", sa.Numeric(8, 2)),
        sa.Column("rent_trend_3mo", sa.Numeric(6, 3)),
        sa.Column("rent_trend_12mo", sa.Numeric(6, 3)),
        sa.Column("net_absorption_sqft", sa.Integer),
        sa.Column("heat_score", sa.Integer),
        sa.Column("narrative", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # --- agent_runs ---
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("agent_name", sa.String(100)),
        sa.Column("started_at", sa.DateTime),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("status", sa.String(20)),
        sa.Column("records_fetched", sa.Integer),
        sa.Column("records_upserted", sa.Integer),
        sa.Column("error_messages", ARRAY(sa.Text), server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("agent_runs")
    op.drop_table("submarket_stats")
    op.drop_table("deal_notes")
    op.drop_table("comps")
    op.drop_table("deals")
    op.drop_table("listings")
    op.drop_table("transactions")
    op.drop_table("buildings")
    op.drop_table("parcels")
