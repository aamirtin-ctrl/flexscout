from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session, verify_api_key

router = APIRouter(prefix="/pipeline", tags=["pipeline"], dependencies=[Depends(verify_api_key)])


@router.get("")
async def get_pipeline(session: AsyncSession = Depends(get_session)):
    result = await session.execute(text("""
        SELECT d.id, d.deal_type, d.score, d.tier, d.narrative, d.risk_flags, d.upside_flags,
            d.status, d.assigned_to, d.created_at, d.updated_at,
            p.address, p.lat, p.lng, p.acreage, p.zoning_code, p.county,
            p.is_delinquent, p.land_value
        FROM deals d
        LEFT JOIN parcels p ON d.parcel_id = p.id
        WHERE d.score >= 40
        ORDER BY d.score DESC
    """))
    rows = result.mappings().all()

    pipeline = {"new": [], "researching": [], "underwriting": [], "active": [], "pass": []}

    for r in rows:
        deal = {
            "id": r["id"],
            "deal_type": r["deal_type"],
            "score": r["score"],
            "tier": r["tier"],
            "narrative": r["narrative"],
            "risk_flags": r["risk_flags"] or [],
            "upside_flags": r["upside_flags"] or [],
            "status": r["status"],
            "assigned_to": r["assigned_to"],
            "parcel": {
                "address": r["address"],
                "lat": float(r["lat"]) if r["lat"] else None,
                "lng": float(r["lng"]) if r["lng"] else None,
                "acreage": float(r["acreage"]) if r["acreage"] else None,
                "zoning_code": r["zoning_code"],
                "county": r["county"],
                "is_delinquent": r["is_delinquent"],
                "land_value": r["land_value"],
            },
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        }
        status_key = r["status"] or "new"
        if status_key in pipeline:
            pipeline[status_key].append(deal)
        else:
            pipeline["new"].append(deal)

    return pipeline
