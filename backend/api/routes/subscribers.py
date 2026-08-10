"""DB-backed alert subscribers. Each subscriber has a JSONB `filters` blob that
the MarketDigestAgent evaluates every Mon + Thu.

Filter shape (all optional):
  {
    "min_lease_rate_nnn":      13,      # $/sqft threshold for flex lease rates
    "min_new_build_rent_nnn":  16,      # $/sqft — only for is_new_construction = true
    "max_land_price_per_sqft": 10,      # $/sqft for land deals
    "max_vacancy_rate":        0.04,    # 4% — emerging-market vacancy threshold
    "market_type":             "emerging" | "primary",
    "min_deal_score":          70,
    "county":                  "dallas" | "tarrant"
  }
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session, verify_api_key

router = APIRouter(prefix="/subscribers", tags=["subscribers"], dependencies=[Depends(verify_api_key)])


class SubscriberFilters(BaseModel):
    min_lease_rate_nnn: Optional[float] = None
    min_new_build_rent_nnn: Optional[float] = None
    max_land_price_per_sqft: Optional[float] = None
    max_vacancy_rate: Optional[float] = None
    market_type: Optional[str] = None  # "emerging" | "primary"
    min_deal_score: Optional[int] = None
    county: Optional[str] = None


class SubscriberIn(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    filters: SubscriberFilters = Field(default_factory=SubscriberFilters)
    delivery: str = "digest"  # digest | email | sms
    frequency: str = "2x_weekly"
    active: bool = True


class SubscriberPatch(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    filters: Optional[SubscriberFilters] = None
    delivery: Optional[str] = None
    frequency: Optional[str] = None
    active: Optional[bool] = None


def _serialize(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
        "filters": row["filters"] or {},
        "delivery": row["delivery"],
        "frequency": row["frequency"],
        "active": row["active"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


@router.get("")
async def list_subscribers(
    session: AsyncSession = Depends(get_session),
    active_only: bool = False,
):
    where = "WHERE active = true" if active_only else ""
    result = await session.execute(
        text(f"SELECT * FROM alert_subscribers {where} ORDER BY created_at DESC")
    )
    return {"subscribers": [_serialize(r) for r in result.mappings().all()]}


@router.post("")
async def create_subscriber(
    body: SubscriberIn,
    session: AsyncSession = Depends(get_session),
):
    import json
    result = await session.execute(
        text("""
            INSERT INTO alert_subscribers (name, email, phone, filters, delivery, frequency, active)
            VALUES (:name, :email, :phone, CAST(:filters AS JSONB), :delivery, :frequency, :active)
            RETURNING *
        """),
        {
            "name": body.name,
            "email": body.email,
            "phone": body.phone,
            "filters": json.dumps(body.filters.model_dump(exclude_none=True)),
            "delivery": body.delivery,
            "frequency": body.frequency,
            "active": body.active,
        },
    )
    row = result.mappings().first()
    await session.commit()
    return _serialize(row)


@router.get("/{sub_id}")
async def get_subscriber(sub_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        text("SELECT * FROM alert_subscribers WHERE id = :id"), {"id": sub_id}
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(404, "Subscriber not found")
    return _serialize(row)


@router.patch("/{sub_id}")
async def update_subscriber(
    sub_id: int,
    body: SubscriberPatch,
    session: AsyncSession = Depends(get_session),
):
    import json
    sets = []
    params: dict = {"id": sub_id}
    for field in ("name", "email", "phone", "delivery", "frequency", "active"):
        val = getattr(body, field)
        if val is not None:
            sets.append(f"{field} = :{field}")
            params[field] = val
    if body.filters is not None:
        sets.append("filters = CAST(:filters AS JSONB)")
        params["filters"] = json.dumps(body.filters.model_dump(exclude_none=True))
    if not sets:
        return await get_subscriber(sub_id, session)
    sets.append("updated_at = NOW()")
    await session.execute(
        text(f"UPDATE alert_subscribers SET {', '.join(sets)} WHERE id = :id"), params
    )
    await session.commit()
    return await get_subscriber(sub_id, session)


@router.delete("/{sub_id}")
async def delete_subscriber(sub_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        text("DELETE FROM alert_subscribers WHERE id = :id RETURNING id"), {"id": sub_id}
    )
    if not result.scalar():
        raise HTTPException(404, "Subscriber not found")
    await session.commit()
    return {"ok": True}


@router.post("/{sub_id}/preview")
async def preview_digest(sub_id: int, session: AsyncSession = Depends(get_session)):
    """Dry-run the digest agent for a single subscriber — does not persist."""
    result = await session.execute(
        text("SELECT id, name, filters FROM alert_subscribers WHERE id = :id"),
        {"id": sub_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(404, "Subscriber not found")

    from agents.alerts.digest_agent import MarketDigestAgent
    agent = MarketDigestAgent()
    payload = await agent._build_payload(session, row["filters"] or {})
    return {
        "subscriber_id": sub_id,
        "match_count": (
            len(payload["emerging_markets"])
            + len(payload["matching_listings"])
            + len(payload["matching_deals"])
        ),
        "payload": payload,
    }
