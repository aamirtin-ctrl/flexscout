from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session, verify_api_key

router = APIRouter(prefix="/market", tags=["market"], dependencies=[Depends(verify_api_key)])


@router.get("/overview")
async def market_overview(session: AsyncSession = Depends(get_session)):
    # Get latest stats across all submarkets
    result = await session.execute(text("""
        SELECT
            AVG(vacancy_rate) AS overall_vacancy_rate,
            AVG(avg_asking_rent_nnn) AS avg_asking_rent_nnn,
            AVG(rent_trend_12mo) AS rent_trend_12mo,
            MAX(as_of_date) AS as_of
        FROM submarket_stats
        WHERE as_of_date = (SELECT MAX(as_of_date) FROM submarket_stats)
    """))
    overview = result.mappings().first()

    listing_count_result = await session.execute(
        text("SELECT COUNT(*) FROM listings WHERE status IS NULL OR status != 'sold'")
    )
    listing_count = listing_count_result.scalar()

    subs_result = await session.execute(text("""
        SELECT submarket_name, vacancy_rate, avg_asking_rent_nnn, rent_trend_12mo, heat_score
        FROM submarket_stats
        WHERE as_of_date = (SELECT MAX(as_of_date) FROM submarket_stats)
        ORDER BY heat_score DESC NULLS LAST
    """))
    submarkets = [
        {
            "name": r["submarket_name"],
            "vacancy_rate": float(r["vacancy_rate"]) if r["vacancy_rate"] else None,
            "avg_asking_rent_nnn": float(r["avg_asking_rent_nnn"]) if r["avg_asking_rent_nnn"] else None,
            "rent_trend_12mo": float(r["rent_trend_12mo"]) if r["rent_trend_12mo"] else None,
            "heat_score": r["heat_score"],
        }
        for r in subs_result.mappings().all()
    ]

    return {
        "as_of": str(overview["as_of"]) if overview and overview["as_of"] else None,
        "overall_vacancy_rate": float(overview["overall_vacancy_rate"]) if overview and overview["overall_vacancy_rate"] else None,
        "avg_asking_rent_nnn": float(overview["avg_asking_rent_nnn"]) if overview and overview["avg_asking_rent_nnn"] else None,
        "rent_trend_12mo": float(overview["rent_trend_12mo"]) if overview and overview["rent_trend_12mo"] else None,
        "active_listing_count": listing_count,
        "submarkets": submarkets,
    }


@router.get("/submarkets")
async def list_submarkets(session: AsyncSession = Depends(get_session)):
    result = await session.execute(text("""
        SELECT * FROM submarket_stats
        WHERE as_of_date = (SELECT MAX(as_of_date) FROM submarket_stats)
        ORDER BY heat_score DESC NULLS LAST
    """))
    return {
        "submarkets": [
            {
                "name": r["submarket_name"],
                "as_of_date": str(r["as_of_date"]) if r["as_of_date"] else None,
                "vacancy_rate": float(r["vacancy_rate"]) if r["vacancy_rate"] else None,
                "avg_asking_rent_nnn": float(r["avg_asking_rent_nnn"]) if r["avg_asking_rent_nnn"] else None,
                "rent_trend_3mo": float(r["rent_trend_3mo"]) if r["rent_trend_3mo"] else None,
                "rent_trend_12mo": float(r["rent_trend_12mo"]) if r["rent_trend_12mo"] else None,
                "net_absorption_sqft": r["net_absorption_sqft"],
                "heat_score": r["heat_score"],
                "narrative": r["narrative"],
            }
            for r in result.mappings().all()
        ]
    }


@router.get("/submarkets/{name}")
async def get_submarket(name: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        text("""
            SELECT * FROM submarket_stats
            WHERE submarket_name = :name
            ORDER BY as_of_date DESC
            LIMIT 12
        """),
        {"name": name},
    )
    rows = result.mappings().all()
    if not rows:
        from fastapi import HTTPException
        raise HTTPException(404, "Submarket not found")

    latest = rows[0]
    history = [
        {
            "month": str(r["as_of_date"]) if r["as_of_date"] else None,
            "vacancy_rate": float(r["vacancy_rate"]) if r["vacancy_rate"] else None,
            "avg_rent": float(r["avg_asking_rent_nnn"]) if r["avg_asking_rent_nnn"] else None,
        }
        for r in reversed(rows)
    ]

    return {
        "name": latest["submarket_name"],
        "vacancy_rate": float(latest["vacancy_rate"]) if latest["vacancy_rate"] else None,
        "avg_asking_rent_nnn": float(latest["avg_asking_rent_nnn"]) if latest["avg_asking_rent_nnn"] else None,
        "rent_trend_12mo": float(latest["rent_trend_12mo"]) if latest["rent_trend_12mo"] else None,
        "heat_score": latest["heat_score"],
        "narrative": latest["narrative"],
        "history": history,
    }


@router.get("/listings")
async def list_market_listings(
    session: AsyncSession = Depends(get_session),
    submarket: Optional[str] = None,
    metro: Optional[str] = None,
    min_sqft: Optional[int] = None,
    max_sqft: Optional[int] = None,
    max_price_per_sqft: Optional[float] = None,
    min_lease_rate_nnn: Optional[float] = None,
    min_new_build_rent_nnn: Optional[float] = None,
    max_land_price_per_sqft: Optional[float] = None,
    is_new_construction: Optional[bool] = None,
    sort_by: str = "listing_date",
    limit: int = Query(default=20, le=100),
):
    conditions = ["1=1"]
    params: dict = {"limit": limit}

    if metro:
        conditions.append("LOWER(metro) = LOWER(:metro)")
        params["metro"] = metro
    if min_sqft is not None:
        conditions.append("sqft >= :min_sqft")
        params["min_sqft"] = min_sqft
    if max_sqft is not None:
        conditions.append("sqft <= :max_sqft")
        params["max_sqft"] = max_sqft
    if max_price_per_sqft is not None:
        conditions.append("price_per_sqft <= :max_ppsf")
        params["max_ppsf"] = max_price_per_sqft
    if min_lease_rate_nnn is not None:
        conditions.append("lease_rate_nnn >= :min_lr")
        params["min_lr"] = min_lease_rate_nnn
    if min_new_build_rent_nnn is not None:
        conditions.append("(is_new_construction = true AND lease_rate_nnn >= :min_nb)")
        params["min_nb"] = min_new_build_rent_nnn
    if max_land_price_per_sqft is not None:
        conditions.append("land_price_per_sqft <= :max_lp")
        params["max_lp"] = max_land_price_per_sqft
    if is_new_construction is not None:
        conditions.append("is_new_construction = :inc")
        params["inc"] = is_new_construction

    where = " AND ".join(conditions)
    sort_map = {
        "listing_date": "listing_date DESC",
        "price": "list_price ASC",
        "sqft": "sqft DESC",
        "lease_rate": "lease_rate_nnn DESC NULLS LAST",
    }
    order = sort_map.get(sort_by, "listing_date DESC")

    result = await session.execute(
        text(f"""
            SELECT id, source, address, metro, state, lat, lng, list_price, price_per_sqft,
                lease_rate_nnn, is_new_construction, land_price_per_sqft, sqft,
                property_type, listing_date, days_on_market, status, year_built
            FROM listings
            WHERE {where}
            ORDER BY {order}
            LIMIT :limit
        """),
        params,
    )
    float_cols = {"lat", "lng", "price_per_sqft", "lease_rate_nnn", "land_price_per_sqft"}
    return {
        "listings": [
            {
                **{k: (float(v) if k in float_cols and v is not None else v) for k, v in dict(r).items()},
                "listing_date": str(r["listing_date"]) if r["listing_date"] else None,
            }
            for r in result.mappings().all()
        ]
    }


@router.get("/national")
async def list_national_markets(
    session: AsyncSession = Depends(get_session),
    max_vacancy_rate: Optional[float] = None,
    min_avg_rent: Optional[float] = None,
    max_land_price_per_sqft: Optional[float] = None,
    market_type: Optional[str] = None,  # "emerging" | "primary"
    state: Optional[str] = None,
    sort_by: str = "vacancy",
    limit: int = Query(default=100, le=500),
):
    """Latest national market snapshot (one row per metro — latest as_of_date)."""
    conds = []
    params: dict = {"limit": limit}
    if max_vacancy_rate is not None:
        conds.append("vacancy_rate <= :max_vac")
        params["max_vac"] = max_vacancy_rate
    if min_avg_rent is not None:
        conds.append("avg_asking_rent_nnn >= :min_rent")
        params["min_rent"] = min_avg_rent
    if max_land_price_per_sqft is not None:
        conds.append("avg_land_price_per_sqft <= :max_lp")
        params["max_lp"] = max_land_price_per_sqft
    if market_type:
        conds.append("market_type = :mtype")
        params["mtype"] = market_type
    if state:
        conds.append("UPPER(state) = UPPER(:st)")
        params["st"] = state
    where = (" WHERE " + " AND ".join(conds)) if conds else ""

    sort_map = {
        "vacancy": "vacancy_rate ASC NULLS LAST",
        "rent": "avg_asking_rent_nnn DESC NULLS LAST",
        "land_cost": "avg_land_price_per_sqft ASC NULLS LAST",
        "metro": "metro ASC",
    }
    order = sort_map.get(sort_by, "vacancy_rate ASC NULLS LAST")

    result = await session.execute(
        text(f"""
            SELECT DISTINCT ON (metro)
                id, metro, state, market_type, vacancy_rate, avg_asking_rent_nnn,
                avg_land_price_per_sqft, rent_yoy_pct, net_absorption_sqft,
                under_construction_sqft, source, source_url, as_of_date
            FROM national_markets
            {where}
            ORDER BY metro, as_of_date DESC NULLS LAST
            LIMIT :limit
        """),
        params,
    )
    rows = result.mappings().all()
    markets = [
        {
            "id": r["id"],
            "metro": r["metro"],
            "state": r["state"],
            "market_type": r["market_type"],
            "vacancy_rate": float(r["vacancy_rate"]) if r["vacancy_rate"] is not None else None,
            "avg_asking_rent_nnn": float(r["avg_asking_rent_nnn"]) if r["avg_asking_rent_nnn"] is not None else None,
            "avg_land_price_per_sqft": float(r["avg_land_price_per_sqft"]) if r["avg_land_price_per_sqft"] is not None else None,
            "rent_yoy_pct": float(r["rent_yoy_pct"]) if r["rent_yoy_pct"] is not None else None,
            "net_absorption_sqft": r["net_absorption_sqft"],
            "under_construction_sqft": r["under_construction_sqft"],
            "source": r["source"],
            "source_url": r["source_url"],
            "as_of_date": str(r["as_of_date"]) if r["as_of_date"] else None,
        }
        for r in rows
    ]
    # Apply python-side sort for non-vacancy modes (DISTINCT ON forces metro-first ORDER)
    if sort_by != "metro":
        key_map = {
            "vacancy": lambda m: (m["vacancy_rate"] is None, m["vacancy_rate"] or 0),
            "rent": lambda m: (m["avg_asking_rent_nnn"] is None, -(m["avg_asking_rent_nnn"] or 0)),
            "land_cost": lambda m: (m["avg_land_price_per_sqft"] is None, m["avg_land_price_per_sqft"] or 0),
        }
        if sort_by in key_map:
            markets.sort(key=key_map[sort_by])
    return {"count": len(markets), "markets": markets}
