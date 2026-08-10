import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agents.base import BaseAgent
from agents.scoring.land_deal_scorer import LandDealScorer
from db import async_session

logger = logging.getLogger(__name__)

FLEX_ZONES = ["IR", "LI", "IM", "CS", "M-1", "M-2", "BC", "BP"]

CANDIDATE_QUERY_LAND = """
    SELECT p.* FROM parcels p
    LEFT JOIN deals d ON p.id = d.parcel_id AND d.deal_type = 'land'
    WHERE d.id IS NULL
      AND p.zoning_code = ANY(:flex_zones)
      AND (p.is_vacant = true OR p.imprv_value < 50000)
      AND p.acreage BETWEEN 0.5 AND 15
    ORDER BY p.updated_at DESC
    LIMIT 100
"""


class DealScoringAgent(BaseAgent):
    name = "deal_scoring"
    schedule = ""  # triggered after comp engine

    def __init__(self):
        super().__init__()
        self.land_scorer = LandDealScorer()

    async def fetch(self) -> list[dict]:
        return []  # not used — run() is overridden

    async def normalize(self, raw: list[dict]) -> list[dict]:
        return raw

    async def upsert(self, session: AsyncSession, records: list[dict]) -> int:
        return 0

    async def run(self) -> None:
        started_at = datetime.utcnow()
        errors: list[str] = []
        scored = 0

        try:
            async with async_session() as session:
                # Get unscored land candidates
                result = await session.execute(
                    text(CANDIDATE_QUERY_LAND),
                    {"flex_zones": FLEX_ZONES},
                )
                candidates = result.mappings().all()
                self.logger.info(f"[{self.name}] Found {len(candidates)} unscored land candidates")

                for parcel in candidates:
                    try:
                        parcel_dict = dict(parcel)

                        # Get comps for this parcel
                        comps_result = await session.execute(
                            text("""
                                SELECT c.*, p.address
                                FROM comps c
                                LEFT JOIN parcels p ON c.comp_parcel_id = p.id
                                WHERE c.subject_parcel_id = :pid
                                ORDER BY c.distance_miles
                                LIMIT 10
                            """),
                            {"pid": parcel_dict["id"]},
                        )
                        comps = [dict(r._mapping) for r in comps_result]

                        # Get nearest submarket stats
                        submarket = None
                        if parcel_dict.get("lat") and parcel_dict.get("lng"):
                            sub_result = await session.execute(
                                text("""
                                    SELECT * FROM submarket_stats
                                    ORDER BY as_of_date DESC NULLS LAST
                                    LIMIT 1
                                """)
                            )
                            row = sub_result.mappings().first()
                            if row:
                                submarket = dict(row)

                        # Build input package and score
                        data = self.land_scorer.build_input_package(parcel_dict, comps, submarket)
                        result = await self.land_scorer.score(data)

                        # Insert deal record
                        await session.execute(
                            text("""
                                INSERT INTO deals (deal_type, parcel_id, score, tier, narrative,
                                    risk_flags, upside_flags, rec_action, status, scored_at)
                                VALUES ('land', :parcel_id, :score, :tier, :narrative,
                                    :risk_flags, :upside_flags, :rec_action, 'new', NOW())
                            """),
                            {
                                "parcel_id": parcel_dict["id"],
                                "score": result.score,
                                "tier": result.tier,
                                "narrative": result.narrative,
                                "risk_flags": result.risk_flags,
                                "upside_flags": result.upside_flags,
                                "rec_action": result.rec_action,
                            },
                        )
                        scored += 1
                        self.logger.info(
                            f"[{self.name}] Scored parcel {parcel_dict['id']}: "
                            f"{result.tier} ({result.score})"
                        )

                    except Exception as e:
                        self.logger.warning(f"[{self.name}] Failed to score parcel {parcel.get('id')}: {e}")
                        errors.append(f"parcel {parcel.get('id')}: {e}")

                await session.commit()

            status = "success" if not errors else ("partial" if scored > 0 else "failed")
            self.logger.info(f"[{self.name}] Scored {scored} deals, {len(errors)} errors")

        except Exception as e:
            self.logger.error(f"[{self.name}] Fatal: {e}", exc_info=True)
            status = "failed"
            errors.append(str(e))

        await self.log_run(status, len(candidates) if 'candidates' in dir() else 0, scored, errors, started_at)
