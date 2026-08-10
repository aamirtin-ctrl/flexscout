from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import anthropic

from config import settings

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "land_v1.txt"


@dataclass
class ScoringResult:
    score: int
    tier: str
    narrative: str
    risk_flags: list[str]
    upside_flags: list[str]
    rec_action: str
    estimated_fair_value_per_acre: int | None = None


class LandDealScorer:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.prompt_template = PROMPT_PATH.read_text()

    async def score(self, data: dict) -> ScoringResult:
        prompt = self.prompt_template.format(data_json=json.dumps(data, indent=2))

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        # Strip any accidental markdown fences
        raw = re.sub(r"```json|```", "", raw).strip()

        result = json.loads(raw)
        return ScoringResult(
            score=result["score"],
            tier=result["tier"],
            narrative=result["narrative"],
            risk_flags=result.get("risk_flags", []),
            upside_flags=result.get("upside_flags", []),
            rec_action=result["rec_action"],
            estimated_fair_value_per_acre=result.get("estimated_fair_value_per_acre"),
        )

    def build_input_package(
        self,
        parcel: dict,
        comps: list[dict],
        submarket: dict | None,
    ) -> dict:
        """Build the data package sent to Claude for scoring."""
        comp_prices = [c["price_per_acre"] for c in comps if c.get("price_per_acre")]

        # Determine seller signals
        signals = []
        if parcel.get("is_delinquent"):
            signals.append("delinquent")
        if parcel.get("owner_since"):
            from datetime import date
            years = (date.today() - parcel["owner_since"]).days / 365.25
            if years > 7:
                signals.append("long_hold")

        # Determine zoning permissions
        flex_codes = {"IR", "LI", "IM", "CS", "M-1", "M-2", "BC", "BP"}
        zoning_code = parcel.get("zoning_code") or ""
        allows_flex = zoning_code in flex_codes

        return {
            "parcel": {
                "address": parcel.get("address"),
                "county": parcel.get("county"),
                "acreage": float(parcel.get("acreage") or 0),
                "zoning_code": zoning_code,
                "zoning_desc": parcel.get("zoning_desc"),
                "land_value_assessed": parcel.get("land_value"),
                "asking_price": None,
                "owner_since_years": round(
                    (date.today() - parcel["owner_since"]).days / 365.25, 1
                ) if parcel.get("owner_since") else None,
                "is_delinquent": parcel.get("is_delinquent", False),
                "delinquency_amt": parcel.get("delinquency_amt"),
                "seller_signals": signals,
            },
            "comps": {
                "count": len(comps),
                "median_price_per_acre": int(sorted(comp_prices)[len(comp_prices) // 2]) if comp_prices else None,
                "min_price_per_acre": min(comp_prices) if comp_prices else None,
                "max_price_per_acre": max(comp_prices) if comp_prices else None,
                "comp_list": [
                    {
                        "address": c.get("address"),
                        "sale_date": str(c.get("sale_date")) if c.get("sale_date") else None,
                        "price_per_acre": c.get("price_per_acre"),
                        "distance_miles": c.get("distance_miles"),
                    }
                    for c in comps[:5]
                ],
            },
            "submarket": {
                "name": submarket.get("submarket_name") if submarket else "Unknown",
                "flex_vacancy_rate": float(submarket["vacancy_rate"]) if submarket and submarket.get("vacancy_rate") else None,
                "avg_asking_rent_nnn": float(submarket["avg_asking_rent_nnn"]) if submarket and submarket.get("avg_asking_rent_nnn") else None,
                "rent_trend_12mo_pct": float(submarket["rent_trend_12mo"]) if submarket and submarket.get("rent_trend_12mo") else None,
                "heat_score": submarket.get("heat_score") if submarket else None,
            },
            "zoning": {
                "allows_flex": allows_flex,
                "allows_warehouse": zoning_code in {"LI", "IM", "M-1", "M-2"},
                "rezoning_needed": not allows_flex,
            },
            "access": {
                "nearest_highway": None,
                "highway_distance_miles": None,
            },
        }
