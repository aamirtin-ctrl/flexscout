from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session, verify_api_key

router = APIRouter(prefix="/parcels", tags=["parcels"], dependencies=[Depends(verify_api_key)])


@router.get("")
async def list_parcels(
    session: AsyncSession = Depends(get_session),
    county: Optional[str] = None,
    zoning_code: Optional[str] = None,
    min_acres: Optional[float] = None,
    max_acres: Optional[float] = None,
    is_vacant: Optional[bool] = None,
    is_delinquent: Optional[bool] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_miles: Optional[float] = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
):
    conditions = ["1=1"]
    params: dict = {"limit": limit, "offset": offset}

    if county:
        conditions.append("county = :county")
        params["county"] = county
    if zoning_code:
        conditions.append("zoning_code = :zoning_code")
        params["zoning_code"] = zoning_code
    if min_acres is not None:
        conditions.append("acreage >= :min_acres")
        params["min_acres"] = min_acres
    if max_acres is not None:
        conditions.append("acreage <= :max_acres")
        params["max_acres"] = max_acres
    if is_vacant is not None:
        conditions.append("is_vacant = :is_vacant")
        params["is_vacant"] = is_vacant
    if is_delinquent is not None:
        conditions.append("is_delinquent = :is_delinquent")
        params["is_delinquent"] = is_delinquent
    if lat and lng and radius_miles:
        conditions.append(
            "ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :radius_m)"
        )
        params["lat"] = lat
        params["lng"] = lng
        params["radius_m"] = radius_miles * 1609.34

    where = " AND ".join(conditions)

    result = await session.execute(
        text(f"""
            SELECT id, apn, county, address, lat, lng, acreage, zoning_code, land_use_code,
                land_value, imprv_value, owner_name, owner_since, is_vacant, is_delinquent,
                delinquency_amt
            FROM parcels
            WHERE {where}
            ORDER BY updated_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    rows = result.mappings().all()

    return {
        "count": len(rows),
        "parcels": [
            {
                **{k: (float(v) if k in ("lat", "lng", "acreage") and v else v) for k, v in dict(r).items()},
                "owner_since": str(r["owner_since"]) if r["owner_since"] else None,
            }
            for r in rows
        ],
    }


@router.get("/{parcel_id}")
async def get_parcel(parcel_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        text("SELECT * FROM parcels WHERE id = :id"), {"id": parcel_id}
    )
    row = result.mappings().first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, "Parcel not found")
    r = dict(row)
    for k in ("lat", "lng", "acreage"):
        if r.get(k):
            r[k] = float(r[k])
    if r.get("owner_since"):
        r["owner_since"] = str(r["owner_since"])
    r.pop("geom", None)
    r["created_at"] = r["created_at"].isoformat() if r.get("created_at") else None
    r["updated_at"] = r["updated_at"].isoformat() if r.get("updated_at") else None
    return r


@router.get("/{parcel_id}/comps")
async def get_parcel_comps(
    parcel_id: int,
    session: AsyncSession = Depends(get_session),
    radius_miles: float = 1.5,
    months_back: int = 24,
    limit: int = 10,
):
    result = await session.execute(
        text("""
            SELECT c.*, p.address AS comp_address
            FROM comps c
            LEFT JOIN parcels p ON c.comp_parcel_id = p.id
            WHERE c.subject_parcel_id = :pid
            ORDER BY c.distance_miles
            LIMIT :limit
        """),
        {"pid": parcel_id, "limit": limit},
    )
    rows = result.mappings().all()
    return {
        "count": len(rows),
        "comps": [
            {
                "address": r["comp_address"],
                "sale_date": str(r["sale_date"]) if r["sale_date"] else None,
                "sale_price": r["sale_price"],
                "price_per_sqft": float(r["price_per_sqft"]) if r["price_per_sqft"] else None,
                "price_per_acre": r["price_per_acre"],
                "acreage": float(r["acreage"]) if r["acreage"] else None,
                "distance_miles": float(r["distance_miles"]) if r["distance_miles"] else None,
            }
            for r in rows
        ],
    }
