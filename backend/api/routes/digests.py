"""Market digest history — read-only view of payloads produced by MarketDigestAgent."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session, verify_api_key

router = APIRouter(prefix="/digests", tags=["digests"], dependencies=[Depends(verify_api_key)])


@router.get("")
async def list_digests(
    session: AsyncSession = Depends(get_session),
    subscriber_id: Optional[int] = None,
    limit: int = Query(default=20, le=100),
):
    conds = []
    params: dict = {"limit": limit}
    if subscriber_id is not None:
        conds.append("d.subscriber_id = :sid")
        params["sid"] = subscriber_id
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    result = await session.execute(
        text(f"""
            SELECT d.id, d.subscriber_id, d.generated_at, d.period_start, d.period_end,
                d.match_count, s.name AS subscriber_name
            FROM market_digests d
            LEFT JOIN alert_subscribers s ON s.id = d.subscriber_id
            {where}
            ORDER BY d.generated_at DESC
            LIMIT :limit
        """),
        params,
    )
    return {
        "digests": [
            {
                "id": r["id"],
                "subscriber_id": r["subscriber_id"],
                "subscriber_name": r["subscriber_name"],
                "generated_at": r["generated_at"].isoformat() if r["generated_at"] else None,
                "period_start": str(r["period_start"]) if r["period_start"] else None,
                "period_end": str(r["period_end"]) if r["period_end"] else None,
                "match_count": r["match_count"],
            }
            for r in result.mappings().all()
        ]
    }


@router.get("/{digest_id}")
async def get_digest(digest_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        text("""
            SELECT d.*, s.name AS subscriber_name
            FROM market_digests d
            LEFT JOIN alert_subscribers s ON s.id = d.subscriber_id
            WHERE d.id = :id
        """),
        {"id": digest_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(404, "Digest not found")
    return {
        "id": row["id"],
        "subscriber_id": row["subscriber_id"],
        "subscriber_name": row["subscriber_name"],
        "generated_at": row["generated_at"].isoformat() if row["generated_at"] else None,
        "period_start": str(row["period_start"]) if row["period_start"] else None,
        "period_end": str(row["period_end"]) if row["period_end"] else None,
        "match_count": row["match_count"],
        "payload": row["payload"] or {},
    }
