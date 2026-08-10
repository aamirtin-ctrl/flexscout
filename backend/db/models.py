from datetime import date, datetime
from typing import List, Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base


class Parcel(Base):
    __tablename__ = "parcels"
    __table_args__ = (
        UniqueConstraint("apn", "county", name="uq_parcels_apn_county"),
        Index("idx_parcels_geom", "geom", postgresql_using="gist"),
        Index("idx_parcels_county", "county"),
        Index("idx_parcels_zoning", "zoning_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    apn: Mapped[str] = mapped_column(String(50), nullable=False)
    county: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text)
    lat: Mapped[Optional[float]] = mapped_column(Numeric(10, 7))
    lng: Mapped[Optional[float]] = mapped_column(Numeric(10, 7))
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    acreage: Mapped[Optional[float]] = mapped_column(Numeric(10, 3))
    zoning_code: Mapped[Optional[str]] = mapped_column(String(20))
    zoning_desc: Mapped[Optional[str]] = mapped_column(Text)
    land_use_code: Mapped[Optional[str]] = mapped_column(String(10))
    land_value: Mapped[Optional[int]] = mapped_column(Integer)
    imprv_value: Mapped[Optional[int]] = mapped_column(Integer)
    owner_name: Mapped[Optional[str]] = mapped_column(Text)
    owner_since: Mapped[Optional[date]] = mapped_column(Date)
    is_vacant: Mapped[bool] = mapped_column(Boolean, default=False)
    is_delinquent: Mapped[bool] = mapped_column(Boolean, default=False)
    delinquency_amt: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    buildings: Mapped[List["Building"]] = relationship(back_populates="parcel")
    deals: Mapped[List["Deal"]] = relationship(back_populates="parcel")
    subject_comps: Mapped[List["Comp"]] = relationship(
        foreign_keys="Comp.subject_parcel_id", back_populates="subject_parcel"
    )


class Building(Base):
    __tablename__ = "buildings"
    __table_args__ = (
        Index("idx_buildings_geom", "geom", postgresql_using="gist"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parcel_id: Mapped[Optional[int]] = mapped_column(ForeignKey("parcels.id"))
    apn: Mapped[Optional[str]] = mapped_column(String(50))
    county: Mapped[Optional[str]] = mapped_column(String(20))
    address: Mapped[Optional[str]] = mapped_column(Text)
    lat: Mapped[Optional[float]] = mapped_column(Numeric(10, 7))
    lng: Mapped[Optional[float]] = mapped_column(Numeric(10, 7))
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    sqft: Mapped[Optional[int]] = mapped_column(Integer)
    year_built: Mapped[Optional[int]] = mapped_column(Integer)
    clear_height_ft: Mapped[Optional[int]] = mapped_column(Integer)
    dock_doors: Mapped[Optional[int]] = mapped_column(Integer)
    drive_in_doors: Mapped[Optional[int]] = mapped_column(Integer)
    office_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    last_sale_date: Mapped[Optional[date]] = mapped_column(Date)
    last_sale_price: Mapped[Optional[int]] = mapped_column(Integer)
    source: Mapped[Optional[str]] = mapped_column(String(30))
    source_id: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    parcel: Mapped[Optional["Parcel"]] = relationship(back_populates="buildings")
    deals: Mapped[List["Deal"]] = relationship(back_populates="building")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("doc_number", "county", name="uq_transactions_doc_county"),
        Index("idx_transactions_apn", "apn", "county"),
        Index("idx_transactions_date", "sale_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    apn: Mapped[Optional[str]] = mapped_column(String(50))
    county: Mapped[Optional[str]] = mapped_column(String(20))
    sale_date: Mapped[Optional[date]] = mapped_column(Date)
    sale_price: Mapped[Optional[int]] = mapped_column(Integer)
    price_per_sqft: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    grantor: Mapped[Optional[str]] = mapped_column(Text)
    grantee: Mapped[Optional[str]] = mapped_column(Text)
    instrument_type: Mapped[Optional[str]] = mapped_column(String(10))
    doc_number: Mapped[Optional[str]] = mapped_column(String(50))
    sqft: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_listings_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[Optional[str]] = mapped_column(String(20))
    source_id: Mapped[Optional[str]] = mapped_column(String(100))
    address: Mapped[Optional[str]] = mapped_column(Text)
    lat: Mapped[Optional[float]] = mapped_column(Numeric(10, 7))
    lng: Mapped[Optional[float]] = mapped_column(Numeric(10, 7))
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    list_price: Mapped[Optional[int]] = mapped_column(Integer)
    price_per_sqft: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    lease_rate_nnn: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    is_new_construction: Mapped[bool] = mapped_column(Boolean, default=False)
    land_price_per_sqft: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    metro: Mapped[Optional[str]] = mapped_column(String(60))
    state: Mapped[Optional[str]] = mapped_column(String(4))
    sqft: Mapped[Optional[int]] = mapped_column(Integer)
    property_type: Mapped[Optional[str]] = mapped_column(String(30))
    listing_date: Mapped[Optional[date]] = mapped_column(Date)
    days_on_market: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[Optional[str]] = mapped_column(String(20))
    year_built: Mapped[Optional[int]] = mapped_column(Integer)
    clear_height_ft: Mapped[Optional[int]] = mapped_column(Integer)
    dock_doors: Mapped[Optional[int]] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = (
        Index("idx_deals_score", "score", postgresql_ops={"score": "DESC"}),
        Index("idx_deals_status", "status"),
        Index("idx_deals_type", "deal_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_type: Mapped[str] = mapped_column(String(10), nullable=False)
    parcel_id: Mapped[Optional[int]] = mapped_column(ForeignKey("parcels.id"))
    building_id: Mapped[Optional[int]] = mapped_column(ForeignKey("buildings.id"))
    score: Mapped[Optional[int]] = mapped_column(Integer)
    tier: Mapped[Optional[str]] = mapped_column(String(5))
    narrative: Mapped[Optional[str]] = mapped_column(Text)
    risk_flags = mapped_column(ARRAY(Text), default=list)
    upside_flags = mapped_column(ARRAY(Text), default=list)
    rec_action: Mapped[Optional[str]] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="new")
    assigned_to: Mapped[Optional[str]] = mapped_column(String(100))
    scored_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    parcel: Mapped[Optional["Parcel"]] = relationship(back_populates="deals")
    building: Mapped[Optional["Building"]] = relationship(back_populates="deals")
    notes: Mapped[List["DealNote"]] = relationship(back_populates="deal")


class Comp(Base):
    __tablename__ = "comps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_parcel_id: Mapped[Optional[int]] = mapped_column(ForeignKey("parcels.id"))
    comp_parcel_id: Mapped[Optional[int]] = mapped_column(ForeignKey("parcels.id"))
    distance_miles: Mapped[Optional[float]] = mapped_column(Numeric(6, 3))
    sale_date: Mapped[Optional[date]] = mapped_column(Date)
    sale_price: Mapped[Optional[int]] = mapped_column(Integer)
    price_per_sqft: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    price_per_acre: Mapped[Optional[int]] = mapped_column(Integer)
    sqft: Mapped[Optional[int]] = mapped_column(Integer)
    acreage: Mapped[Optional[float]] = mapped_column(Numeric(10, 3))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    subject_parcel: Mapped[Optional["Parcel"]] = relationship(
        foreign_keys=[subject_parcel_id], back_populates="subject_comps"
    )
    comp_parcel: Mapped[Optional["Parcel"]] = relationship(foreign_keys=[comp_parcel_id])


class DealNote(Base):
    __tablename__ = "deal_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"))
    note: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    deal: Mapped["Deal"] = relationship(back_populates="notes")


class SubmarketStat(Base):
    __tablename__ = "submarket_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submarket_name: Mapped[Optional[str]] = mapped_column(String(100))
    as_of_date: Mapped[Optional[date]] = mapped_column(Date)
    vacancy_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 3))
    avg_asking_rent_nnn: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    rent_trend_3mo: Mapped[Optional[float]] = mapped_column(Numeric(6, 3))
    rent_trend_12mo: Mapped[Optional[float]] = mapped_column(Numeric(6, 3))
    net_absorption_sqft: Mapped[Optional[int]] = mapped_column(Integer)
    heat_score: Mapped[Optional[int]] = mapped_column(Integer)
    narrative: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class NationalMarket(Base):
    __tablename__ = "national_markets"
    __table_args__ = (
        UniqueConstraint("metro", "source", "as_of_date", name="uq_national_markets_metro_src_date"),
        Index("idx_national_markets_vacancy", "vacancy_rate"),
        Index("idx_national_markets_metro", "metro"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metro: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[Optional[str]] = mapped_column(String(4))
    vacancy_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 3))
    avg_asking_rent_nnn: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    avg_land_price_per_sqft: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    rent_yoy_pct: Mapped[Optional[float]] = mapped_column(Numeric(6, 3))
    net_absorption_sqft: Mapped[Optional[int]] = mapped_column(Integer)
    under_construction_sqft: Mapped[Optional[int]] = mapped_column(Integer)
    market_type: Mapped[Optional[str]] = mapped_column(String(20))
    source: Mapped[Optional[str]] = mapped_column(String(40))
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    as_of_date: Mapped[Optional[date]] = mapped_column(Date)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AlertSubscriber(Base):
    __tablename__ = "alert_subscribers"
    __table_args__ = (
        Index("idx_alert_subscribers_active", "active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(180))
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    filters = mapped_column(JSONB, default=dict, nullable=False)
    delivery: Mapped[str] = mapped_column(String(20), default="digest")
    frequency: Mapped[str] = mapped_column(String(20), default="2x_weekly")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    digests: Mapped[List["MarketDigest"]] = relationship(back_populates="subscriber", cascade="all, delete-orphan")


class MarketDigest(Base):
    __tablename__ = "market_digests"
    __table_args__ = (
        Index("idx_market_digests_subscriber", "subscriber_id"),
        Index("idx_market_digests_generated", "generated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscriber_id: Mapped[Optional[int]] = mapped_column(ForeignKey("alert_subscribers.id", ondelete="CASCADE"))
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    period_start: Mapped[Optional[date]] = mapped_column(Date)
    period_end: Mapped[Optional[date]] = mapped_column(Date)
    match_count: Mapped[int] = mapped_column(Integer, default=0)
    payload = mapped_column(JSONB, default=dict, nullable=False)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    subscriber: Mapped[Optional["AlertSubscriber"]] = relationship(back_populates="digests")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_name: Mapped[Optional[str]] = mapped_column(String(100))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[Optional[str]] = mapped_column(String(20))
    records_fetched: Mapped[Optional[int]] = mapped_column(Integer)
    records_upserted: Mapped[Optional[int]] = mapped_column(Integer)
    error_messages = mapped_column(ARRAY(Text), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
