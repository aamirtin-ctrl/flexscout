from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session, verify_api_key

router = APIRouter(prefix="/deals", tags=["deals"], dependencies=[Depends(verify_api_key)])


@router.get("")
async def list_deals(
    session: AsyncSession = Depends(get_session),
    deal_type: str = "all",
    tier: Optional[str] = None,
    min_score: int = 40,
    status: Optional[str] = None,
    submarket: Optional[str] = None,
    county: str = "all",
    signals: Optional[str] = None,
    max_land_price_per_sqft: Optional[float] = None,
    min_acreage: Optional[float] = None,
    max_acreage: Optional[float] = None,
    sort_by: str = "score",
    sort_dir: str = "desc",
    limit: int = Query(default=20, le=100),
    offset: int = 0,
):
    conditions = ["d.score >= :min_score"]
    params: dict = {"min_score": min_score, "limit": limit, "offset": offset}

    if deal_type != "all":
        conditions.append("d.deal_type = :deal_type")
        params["deal_type"] = deal_type

    if tier:
        tiers = [t.strip() for t in tier.split(",")]
        conditions.append("d.tier = ANY(:tiers)")
        params["tiers"] = tiers

    if status:
        statuses = [s.strip() for s in status.split(",")]
        conditions.append("d.status = ANY(:statuses)")
        params["statuses"] = statuses

    if county != "all":
        conditions.append("p.county = :county")
        params["county"] = county

    if submarket:
        conditions.append("ss.submarket_name = :submarket")
        params["submarket"] = submarket

    if max_land_price_per_sqft is not None:
        # land_value is assessed $; acreage * 43560 = sqft. Filter land_value/sqft <= threshold.
        conditions.append(
            "(p.acreage > 0 AND (p.land_value::float / (p.acreage * 43560)) <= :max_land_ppsf)"
        )
        params["max_land_ppsf"] = max_land_price_per_sqft

    if min_acreage is not None:
        conditions.append("p.acreage >= :min_ac")
        params["min_ac"] = min_acreage
    if max_acreage is not None:
        conditions.append("p.acreage <= :max_ac")
        params["max_ac"] = max_acreage

    if signals:
        signal_list = [s.strip() for s in signals.split(",")]
        for i, sig in enumerate(signal_list):
            if sig == "delinquent":
                conditions.append("p.is_delinquent = true")
            elif sig == "long_hold":
                conditions.append("p.owner_since < NOW() - INTERVAL '7 years'")

    where = " AND ".join(conditions)

    sort_map = {"score": "d.score", "date": "d.created_at", "price": "p.land_value"}
    order_col = sort_map.get(sort_by, "d.score")
    order = f"{order_col} {'DESC' if sort_dir == 'desc' else 'ASC'}"

    # Count total
    count_q = f"""
        SELECT COUNT(*) FROM deals d
        LEFT JOIN parcels p ON d.parcel_id = p.id
        LEFT JOIN submarket_stats ss ON 1=0
        WHERE {where}
    """
    total_result = await session.execute(text(count_q), params)
    total = total_result.scalar()

    # Fetch deals
    query = f"""
        SELECT
            d.id, d.deal_type, d.score, d.tier, d.narrative, d.risk_flags, d.upside_flags,
            d.rec_action, d.status, d.assigned_to, d.created_at,
            p.address, p.lat, p.lng, p.acreage, p.zoning_code, p.owner_since,
            p.is_delinquent, p.land_value, p.county,
            (SELECT COUNT(*) FROM comps c WHERE c.subject_parcel_id = p.id) AS comp_count
        FROM deals d
        LEFT JOIN parcels p ON d.parcel_id = p.id
        LEFT JOIN submarket_stats ss ON 1=0
        WHERE {where}
        ORDER BY {order}
        LIMIT :limit OFFSET :offset
    """
    result = await session.execute(text(query), params)
    rows = result.mappings().all()

    deals = []
    for r in rows:
        deals.append({
            "id": r["id"],
            "deal_type": r["deal_type"],
            "score": r["score"],
            "tier": r["tier"],
            "narrative": r["narrative"],
            "risk_flags": r["risk_flags"] or [],
            "upside_flags": r["upside_flags"] or [],
            "rec_action": r["rec_action"],
            "status": r["status"],
            "parcel": {
                "address": r["address"],
                "lat": float(r["lat"]) if r["lat"] else None,
                "lng": float(r["lng"]) if r["lng"] else None,
                "acreage": float(r["acreage"]) if r["acreage"] else None,
                "zoning_code": r["zoning_code"],
                "owner_since": str(r["owner_since"]) if r["owner_since"] else None,
                "is_delinquent": r["is_delinquent"],
                "land_value": r["land_value"],
            },
            "county": r["county"],
            "comp_count": r["comp_count"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })

    return {
        "total": total,
        "count": len(deals),
        "offset": offset,
        "has_more": offset + len(deals) < total,
        "deals": deals,
    }


@router.get("/{deal_id}")
async def get_deal(deal_id: int, session: AsyncSession = Depends(get_session)):
    # Main deal + parcel
    result = await session.execute(
        text("""
            SELECT d.*, p.address, p.lat, p.lng, p.acreage, p.zoning_code, p.zoning_desc,
                p.owner_since, p.is_delinquent, p.delinquency_amt, p.land_value, p.imprv_value,
                p.county, p.owner_name
            FROM deals d
            LEFT JOIN parcels p ON d.parcel_id = p.id
            WHERE d.id = :deal_id
        """),
        {"deal_id": deal_id},
    )
    row = result.mappings().first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, "Deal not found")

    r = dict(row)

    # Comps
    comps_result = await session.execute(
        text("""
            SELECT c.*, p.address AS comp_address
            FROM comps c
            LEFT JOIN parcels p ON c.comp_parcel_id = p.id
            WHERE c.subject_parcel_id = :pid
            ORDER BY c.distance_miles
        """),
        {"pid": r.get("parcel_id")},
    )
    comps = [
        {
            "address": cr["comp_address"],
            "sale_date": str(cr["sale_date"]) if cr["sale_date"] else None,
            "sale_price": cr["sale_price"],
            "price_per_acre": cr["price_per_acre"],
            "acreage": float(cr["acreage"]) if cr["acreage"] else None,
            "distance_miles": float(cr["distance_miles"]) if cr["distance_miles"] else None,
        }
        for cr in comps_result.mappings().all()
    ]

    # Notes
    notes_result = await session.execute(
        text("SELECT * FROM deal_notes WHERE deal_id = :deal_id ORDER BY created_at DESC"),
        {"deal_id": deal_id},
    )
    notes = [
        {"id": n["id"], "note": n["note"], "author": n["author"],
         "created_at": n["created_at"].isoformat() if n["created_at"] else None}
        for n in notes_result.mappings().all()
    ]

    # Submarket
    sub_result = await session.execute(
        text("SELECT * FROM submarket_stats ORDER BY as_of_date DESC NULLS LAST LIMIT 1")
    )
    sub = sub_result.mappings().first()
    submarket_stats = None
    if sub:
        submarket_stats = {
            "name": sub["submarket_name"],
            "vacancy_rate": float(sub["vacancy_rate"]) if sub["vacancy_rate"] else None,
            "avg_asking_rent_nnn": float(sub["avg_asking_rent_nnn"]) if sub["avg_asking_rent_nnn"] else None,
            "rent_trend_12mo": float(sub["rent_trend_12mo"]) if sub["rent_trend_12mo"] else None,
            "heat_score": sub["heat_score"],
        }

    return {
        "id": r["id"],
        "deal_type": r["deal_type"],
        "score": r["score"],
        "tier": r["tier"],
        "narrative": r["narrative"],
        "risk_flags": r["risk_flags"] or [],
        "upside_flags": r["upside_flags"] or [],
        "rec_action": r["rec_action"],
        "status": r["status"],
        "assigned_to": r["assigned_to"],
        "scored_at": r["scored_at"].isoformat() if r.get("scored_at") else None,
        "parcel": {
            "address": r["address"],
            "lat": float(r["lat"]) if r["lat"] else None,
            "lng": float(r["lng"]) if r["lng"] else None,
            "acreage": float(r["acreage"]) if r["acreage"] else None,
            "zoning_code": r["zoning_code"],
            "zoning_desc": r["zoning_desc"],
            "owner_name": r["owner_name"],
            "owner_since": str(r["owner_since"]) if r["owner_since"] else None,
            "is_delinquent": r["is_delinquent"],
            "delinquency_amt": r["delinquency_amt"],
            "land_value": r["land_value"],
            "imprv_value": r["imprv_value"],
            "county": r["county"],
        },
        "comps": comps,
        "submarket_stats": submarket_stats,
        "notes": notes,
        "building": None,
    }


@router.patch("/{deal_id}")
async def update_deal(deal_id: int, body: dict, session: AsyncSession = Depends(get_session)):
    sets = []
    params = {"deal_id": deal_id}

    if "status" in body:
        sets.append("status = :status")
        params["status"] = body["status"]
    if "assigned_to" in body:
        sets.append("assigned_to = :assigned_to")
        params["assigned_to"] = body["assigned_to"]

    if not sets:
        return {"ok": True}

    sets.append("updated_at = NOW()")
    await session.execute(
        text(f"UPDATE deals SET {', '.join(sets)} WHERE id = :deal_id"),
        params,
    )
    await session.commit()
    return {"ok": True}


@router.post("/{deal_id}/notes")
async def add_note(deal_id: int, body: dict, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        text("""
            INSERT INTO deal_notes (deal_id, note, author)
            VALUES (:deal_id, :note, :author)
            RETURNING id, created_at
        """),
        {"deal_id": deal_id, "note": body["note"], "author": body.get("author")},
    )
    row = result.mappings().first()
    await session.commit()
    return {"id": row["id"], "created_at": row["created_at"].isoformat()}
