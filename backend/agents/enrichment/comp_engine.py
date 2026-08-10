import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agents.base import BaseAgent

logger = logging.getLogger(__name__)

FLEX_COMPATIBLE_ZONES = ["IR", "LI", "IM", "CS", "M-1", "M-2", "BC", "BP"]

COMP_QUERY = """
    SELECT
        t.sale_date,
        t.sale_price,
        t.price_per_sqft,
        p.id AS comp_parcel_id,
        p.acreage,
        p.zoning_code,
        ST_Distance(p.geom::geography, subject.geom::geography) / 1609.34 AS distance_miles
    FROM transactions t
    JOIN parcels p ON t.apn = p.apn AND t.county = p.county
    CROSS JOIN (
        SELECT geom FROM parcels WHERE id = :subject_id
    ) subject
    WHERE t.instrument_type = 'WD'
      AND t.sale_date > NOW() - INTERVAL :months_back
      AND p.zoning_code = ANY(:compatible_zones)
      AND ST_DWithin(p.geom::geography, subject.geom::geography, :radius_meters)
      AND p.id != :subject_id
    ORDER BY distance_miles
    LIMIT 10
"""

CANDIDATE_PARCELS_QUERY = """
    SELECT id, acreage
    FROM parcels
    WHERE geom IS NOT NULL
      AND zoning_code = ANY(:flex_zones)
      AND (is_vacant = true OR imprv_value < 50000)
      AND acreage BETWEEN 0.5 AND 15
    ORDER BY updated_at DESC
    LIMIT 500
"""


class CompEngine(BaseAgent):
    name = "comp_engine"
    schedule = ""  # triggered after parcel agents

    def __init__(self, radius_miles: float = 1.5, months_back: int = 24):
        super().__init__()
        self.radius_meters = radius_miles * 1609.34
        self.months_back = months_back

    async def fetch(self) -> list[dict]:
        """Get candidate parcels that need comps."""
        async with (await self._get_session()) as session:
            result = await session.execute(
                text(CANDIDATE_PARCELS_QUERY),
                {"flex_zones": FLEX_COMPATIBLE_ZONES},
            )
            return [{"id": row.id, "acreage": row.acreage} for row in result]

    async def _get_session(self):
        from db import async_session
        return async_session()

    async def normalize(self, raw: list[dict]) -> list[dict]:
        return raw  # pass-through — comp query runs in upsert

    async def upsert(self, session: AsyncSession, records: list[dict]) -> int:
        total_comps = 0

        for parcel in records:
            subject_id = parcel["id"]

            # Delete existing comps for this parcel (refresh)
            await session.execute(
                text("DELETE FROM comps WHERE subject_parcel_id = :sid"),
                {"sid": subject_id},
            )

            result = await session.execute(
                text(COMP_QUERY),
                {
                    "subject_id": subject_id,
                    "months_back": f"{self.months_back} months",
                    "compatible_zones": FLEX_COMPATIBLE_ZONES,
                    "radius_meters": self.radius_meters,
                },
            )

            rows = result.fetchall()
            for row in rows:
                price_per_acre = None
                if row.sale_price and row.acreage and float(row.acreage) > 0:
                    price_per_acre = int(row.sale_price / float(row.acreage))

                await session.execute(
                    text("""
                        INSERT INTO comps (subject_parcel_id, comp_parcel_id, distance_miles,
                            sale_date, sale_price, price_per_sqft, price_per_acre, sqft, acreage)
                        VALUES (:subject_id, :comp_parcel_id, :distance_miles,
                            :sale_date, :sale_price, :price_per_sqft, :price_per_acre, NULL, :acreage)
                    """),
                    {
                        "subject_id": subject_id,
                        "comp_parcel_id": row.comp_parcel_id,
                        "distance_miles": round(float(row.distance_miles), 3),
                        "sale_date": row.sale_date,
                        "sale_price": row.sale_price,
                        "price_per_sqft": float(row.price_per_sqft) if row.price_per_sqft else None,
                        "price_per_acre": price_per_acre,
                        "acreage": float(row.acreage) if row.acreage else None,
                    },
                )
                total_comps += 1

        return total_comps

    async def run(self) -> None:
        """Override to use a single session for fetching candidates."""
        from datetime import datetime
        from db import async_session

        started_at = datetime.utcnow()
        errors: list[str] = []

        try:
            async with async_session() as session:
                result = await session.execute(
                    text(CANDIDATE_PARCELS_QUERY),
                    {"flex_zones": FLEX_COMPATIBLE_ZONES},
                )
                parcels = [{"id": row.id, "acreage": row.acreage} for row in result]
                self.logger.info(f"[{self.name}] Found {len(parcels)} candidate parcels")

                total = await self.upsert(session, parcels)
                await session.commit()

            self.logger.info(f"[{self.name}] Wrote {total} comps")
            await self.log_run("success", len(parcels), total, errors, started_at)
        except Exception as e:
            self.logger.error(f"[{self.name}] Failed: {e}", exc_info=True)
            await self.log_run("failed", 0, 0, [str(e)], started_at)
