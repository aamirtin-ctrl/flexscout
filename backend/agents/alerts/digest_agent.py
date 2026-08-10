"""Market digest agent — runs 2x/week and builds a per-subscriber snapshot.

For each active AlertSubscriber, evaluates its `filters` JSONB against:
  - national_markets  (for "emerging market" watchlists: vacancy < X%)
  - listings          (for lease-rate / new-construction-rent / land-$/sqft alerts)
  - deals             (for DFW parcel matches at >= min_score)

Writes one MarketDigest row per run per subscriber with a JSON payload. SMS/email
delivery is intentionally skipped for now (cost). The in-app Alerts page reads
these rows to render the latest digest.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agents.base import BaseAgent
from db import async_session

logger = logging.getLogger(__name__)


class MarketDigestAgent(BaseAgent):
    name = "market_digest"
    # Mondays + Thursdays at 9am (UTC — adjust via TZ on scheduler if needed)
    schedule = "0 9 * * 1,4"

    async def fetch(self) -> list[dict]:
        """List active subscribers."""
        async with async_session() as session:
            result = await session.execute(
                text("SELECT id, name, filters FROM alert_subscribers WHERE active = true")
            )
            return [dict(r) for r in result.mappings().all()]

    async def normalize(self, raw: list[dict]) -> list[dict]:
        """For each subscriber, build a digest payload."""
        digests: list[dict] = []
        period_end = date.today()
        period_start = period_end - timedelta(days=4)  # 2x/week cadence window

        async with async_session() as session:
            for sub in raw:
                payload = await self._build_payload(session, sub["filters"] or {})
                digests.append({
                    "subscriber_id": sub["id"],
                    "period_start": period_start,
                    "period_end": period_end,
                    "match_count": (
                        len(payload["emerging_markets"])
                        + len(payload["matching_listings"])
                        + len(payload["matching_deals"])
                    ),
                    "payload": payload,
                })
        return digests

    async def _build_payload(self, session: AsyncSession, f: dict) -> dict:
        min_lease_rate = _as_float(f.get("min_lease_rate_nnn"))
        min_new_build_rent = _as_float(f.get("min_new_build_rent_nnn"))
        max_land_cost = _as_float(f.get("max_land_price_per_sqft"))
        max_vacancy = _as_float(f.get("max_vacancy_rate"))
        market_type = f.get("market_type")  # "emerging" | "primary" | None
        min_deal_score = int(f.get("min_deal_score") or 70)
        deal_county = f.get("county")  # e.g. "dallas" | "tarrant"

        # --- Emerging markets (vacancy < X%) ---
        em_conds = []
        em_params: dict = {}
        if max_vacancy is not None:
            em_conds.append("vacancy_rate <= :max_vacancy")
            em_params["max_vacancy"] = max_vacancy
        if market_type:
            em_conds.append("market_type = :market_type")
            em_params["market_type"] = market_type
        em_where = " AND ".join(em_conds) if em_conds else "1=1"
        em_rows = (await session.execute(
            text(f"""
                SELECT DISTINCT ON (metro) metro, state, vacancy_rate, avg_asking_rent_nnn,
                    avg_land_price_per_sqft, market_type, source, as_of_date
                FROM national_markets
                WHERE {em_where}
                ORDER BY metro, as_of_date DESC NULLS LAST
                LIMIT 50
            """),
            em_params,
        )).mappings().all()
        emerging = [
            {
                "metro": r["metro"],
                "state": r["state"],
                "vacancy_rate": float(r["vacancy_rate"]) if r["vacancy_rate"] is not None else None,
                "avg_asking_rent_nnn": float(r["avg_asking_rent_nnn"]) if r["avg_asking_rent_nnn"] is not None else None,
                "avg_land_price_per_sqft": float(r["avg_land_price_per_sqft"]) if r["avg_land_price_per_sqft"] is not None else None,
                "market_type": r["market_type"],
                "source": r["source"],
                "as_of_date": str(r["as_of_date"]) if r["as_of_date"] else None,
            }
            for r in em_rows
        ]

        # --- Listings matching lease-rate / new-build-rent / land-cost thresholds ---
        l_conds = ["1=1"]
        l_params: dict = {}
        if min_lease_rate is not None:
            l_conds.append("lease_rate_nnn >= :min_lease_rate")
            l_params["min_lease_rate"] = min_lease_rate
        if min_new_build_rent is not None:
            l_conds.append("(is_new_construction = true AND lease_rate_nnn >= :min_nb_rent)")
            l_params["min_nb_rent"] = min_new_build_rent
        if max_land_cost is not None:
            l_conds.append("land_price_per_sqft <= :max_land_cost")
            l_params["max_land_cost"] = max_land_cost
        # Only return listings created or updated in the recent window
        l_conds.append("(updated_at >= NOW() - INTERVAL '14 days')")
        l_where = " AND ".join(l_conds)
        l_rows = (await session.execute(
            text(f"""
                SELECT id, address, metro, state, lease_rate_nnn, is_new_construction,
                    land_price_per_sqft, sqft, property_type, list_price, source
                FROM listings
                WHERE {l_where}
                ORDER BY updated_at DESC
                LIMIT 25
            """),
            l_params,
        )).mappings().all()
        listings = [
            {
                "id": r["id"],
                "address": r["address"],
                "metro": r["metro"],
                "state": r["state"],
                "lease_rate_nnn": float(r["lease_rate_nnn"]) if r["lease_rate_nnn"] is not None else None,
                "is_new_construction": r["is_new_construction"],
                "land_price_per_sqft": float(r["land_price_per_sqft"]) if r["land_price_per_sqft"] is not None else None,
                "sqft": r["sqft"],
                "property_type": r["property_type"],
                "list_price": r["list_price"],
                "source": r["source"],
            }
            for r in l_rows
        ]

        # --- DFW deals (highest-scoring recent parcels) ---
        d_conds = ["d.score >= :min_score", "d.created_at >= NOW() - INTERVAL '7 days'"]
        d_params: dict = {"min_score": min_deal_score}
        if deal_county:
            d_conds.append("p.county = :county")
            d_params["county"] = deal_county
        d_where = " AND ".join(d_conds)
        d_rows = (await session.execute(
            text(f"""
                SELECT d.id, d.deal_type, d.score, d.tier, d.narrative, p.address,
                    p.acreage, p.land_value, p.county
                FROM deals d
                LEFT JOIN parcels p ON d.parcel_id = p.id
                WHERE {d_where}
                ORDER BY d.score DESC
                LIMIT 10
            """),
            d_params,
        )).mappings().all()
        deals = [
            {
                "id": r["id"],
                "deal_type": r["deal_type"],
                "score": r["score"],
                "tier": r["tier"],
                "narrative": (r["narrative"] or "")[:280],
                "address": r["address"],
                "acreage": float(r["acreage"]) if r["acreage"] is not None else None,
                "land_value": r["land_value"],
                "county": r["county"],
            }
            for r in d_rows
        ]

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "thresholds": {
                "min_lease_rate_nnn": min_lease_rate,
                "min_new_build_rent_nnn": min_new_build_rent,
                "max_land_price_per_sqft": max_land_cost,
                "max_vacancy_rate": max_vacancy,
                "market_type": market_type,
                "min_deal_score": min_deal_score,
                "county": deal_county,
            },
            "emerging_markets": emerging,
            "matching_listings": listings,
            "matching_deals": deals,
        }

    async def upsert(self, session: AsyncSession, records: list[dict]) -> int:
        if not records:
            return 0
        import json
        count = 0
        for rec in records:
            await session.execute(
                text("""
                    INSERT INTO market_digests (
                        subscriber_id, period_start, period_end, match_count, payload
                    ) VALUES (
                        :subscriber_id, :period_start, :period_end, :match_count, CAST(:payload AS JSONB)
                    )
                """),
                {**rec, "payload": json.dumps(rec["payload"], default=str)},
            )
            count += 1
        return count


def _as_float(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
