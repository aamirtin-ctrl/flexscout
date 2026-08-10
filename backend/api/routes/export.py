from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session, verify_api_key

router = APIRouter(tags=["export"], dependencies=[Depends(verify_api_key)])


@router.get("/deals/export")
async def export_deals_csv(
    session: AsyncSession = Depends(get_session),
    deal_type: str = "all",
    min_score: int = 40,
    tier: str | None = None,
    county: str = "all",
):
    conditions = ["d.score >= :min_score"]
    params: dict = {"min_score": min_score}

    if deal_type != "all":
        conditions.append("d.deal_type = :deal_type")
        params["deal_type"] = deal_type
    if tier:
        tiers = [t.strip() for t in tier.split(",")]
        conditions.append("d.tier = ANY(:tiers)")
        params["tiers"] = tiers
    if county != "all":
        conditions.append("p.county = :county")
        params["county"] = county

    where = " AND ".join(conditions)

    result = await session.execute(
        text(f"""
            SELECT d.deal_type, d.score, d.tier, d.narrative, d.risk_flags, d.upside_flags,
                d.status, p.address, p.acreage, p.zoning_code, p.land_value, p.county,
                p.is_delinquent
            FROM deals d
            LEFT JOIN parcels p ON d.parcel_id = p.id
            WHERE {where}
            ORDER BY d.score DESC
        """),
        params,
    )
    rows = result.mappings().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Address", "Type", "Score", "Tier", "Price", "Acreage", "Zoning",
        "County", "Signals", "Narrative", "Status",
    ])

    for r in rows:
        signals = []
        if r["is_delinquent"]:
            signals.append("Delinquent")
        if r["risk_flags"]:
            signals.extend(r["risk_flags"])

        writer.writerow([
            r["address"],
            r["deal_type"],
            r["score"],
            r["tier"],
            r["land_value"],
            float(r["acreage"]) if r["acreage"] else "",
            r["zoning_code"],
            r["county"],
            "; ".join(signals),
            r["narrative"],
            r["status"],
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=flexscout_deals.csv"},
    )
