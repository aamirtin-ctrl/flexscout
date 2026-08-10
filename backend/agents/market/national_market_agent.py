"""National industrial/flex market data agent.

Pulls metro-level vacancy, asking rent, and supply stats from publicly available
CRE research pages. Primary source is CommercialEdge's monthly National Industrial
Report (https://www.commercialedge.com/blog/national-industrial-report/), with a
fallback scrape of CBRE's quarterly US Industrial Figures page.

No hardcoded metro lists — everything is extracted from the live page content.
If a source's HTML shifts, the agent logs a warning and upserts whatever it
could extract rather than crashing.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Iterable

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agents.base import BaseAgent

logger = logging.getLogger(__name__)

COMMERCIALEDGE_HUB = "https://www.commercialedge.com/blog/category/national-industrial-report/"
COMMERCIALEDGE_LATEST = "https://www.commercialedge.com/blog/national-industrial-report/"
CBRE_FIGURES = "https://www.cbre.com/insights/figures/us-industrial-figures"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# State lookup for common metros (used only to annotate — not to gate inclusion)
METRO_STATE_HINTS = {
    "phoenix": "AZ", "dallas": "TX", "dallas-fort worth": "TX", "fort worth": "TX",
    "houston": "TX", "austin": "TX", "san antonio": "TX", "atlanta": "GA",
    "charlotte": "NC", "nashville": "TN", "indianapolis": "IN", "columbus": "OH",
    "cleveland": "OH", "cincinnati": "OH", "kansas city": "MO", "st. louis": "MO",
    "detroit": "MI", "chicago": "IL", "minneapolis": "MN", "denver": "CO",
    "salt lake city": "UT", "las vegas": "NV", "reno": "NV", "boise": "ID",
    "portland": "OR", "seattle": "WA", "tacoma": "WA", "los angeles": "CA",
    "inland empire": "CA", "orange county": "CA", "san diego": "CA",
    "bay area": "CA", "san francisco": "CA", "san jose": "CA", "sacramento": "CA",
    "stockton": "CA", "miami": "FL", "orlando": "FL", "tampa": "FL",
    "jacksonville": "FL", "new york": "NY", "new jersey": "NJ", "long island": "NY",
    "philadelphia": "PA", "pittsburgh": "PA", "harrisburg": "PA", "boston": "MA",
    "baltimore": "MD", "washington": "DC", "richmond": "VA", "raleigh": "NC",
    "memphis": "TN", "louisville": "KY", "milwaukee": "WI", "omaha": "NE",
    "oklahoma city": "OK", "tulsa": "OK", "albuquerque": "NM",
}

# Emerging vs. primary classification based on typical ranking of industrial
# market size (population proxy). Anything not in PRIMARY is tagged "emerging".
PRIMARY_MARKETS = {
    "los angeles", "inland empire", "new york", "new jersey", "chicago",
    "dallas", "dallas-fort worth", "houston", "atlanta", "philadelphia",
    "boston", "washington", "miami",
}


def _state_for(metro_name: str) -> str | None:
    key = metro_name.lower().strip()
    for hint, state in METRO_STATE_HINTS.items():
        if hint in key:
            return state
    return None


def _classify(metro_name: str) -> str:
    key = metro_name.lower().strip()
    return "primary" if any(p in key for p in PRIMARY_MARKETS) else "emerging"


def _parse_percent(s: str) -> float | None:
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
    return float(m.group(1)) / 100.0 if m else None


def _parse_money(s: str) -> float | None:
    if not s:
        return None
    m = re.search(r"\$?\s*(\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else None


def _parse_int(s: str) -> int | None:
    if not s:
        return None
    cleaned = re.sub(r"[^\d\-]", "", s)
    try:
        return int(cleaned) if cleaned else None
    except ValueError:
        return None


class NationalMarketAgent(BaseAgent):
    name = "national_market"
    # First day of the month at 4am — CommercialEdge publishes early each month
    schedule = "0 4 1 * *"

    async def fetch(self) -> list[dict]:
        async with httpx.AsyncClient(
            timeout=60,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            raws: list[dict] = []
            raws.extend(await self._fetch_commercialedge(client))
            # Secondary attempt — best-effort, not required
            try:
                raws.extend(await self._fetch_cbre(client))
            except Exception as e:
                logger.warning("CBRE fallback skipped: %s", e)
            return raws

    async def _fetch_commercialedge(self, client: httpx.AsyncClient) -> list[dict]:
        """Scrape the latest CommercialEdge National Industrial Report post."""
        # Step 1: find the most recent report URL from the category index
        try:
            hub = await client.get(COMMERCIALEDGE_HUB)
            hub.raise_for_status()
            soup = BeautifulSoup(hub.text, "lxml")
            post_link = None
            for a in soup.select("a[href*='/blog/']"):
                href = a.get("href", "")
                if "national-industrial-report" in href and href != COMMERCIALEDGE_HUB:
                    post_link = href
                    break
            target = post_link or COMMERCIALEDGE_LATEST
        except Exception as e:
            logger.warning("CommercialEdge hub fetch failed, using canonical URL: %s", e)
            target = COMMERCIALEDGE_LATEST

        # Step 2: fetch the report itself and extract the metro table
        try:
            resp = await client.get(target)
            resp.raise_for_status()
        except Exception as e:
            logger.warning("CommercialEdge report fetch failed: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        rows: list[dict] = []
        # The post has tables — parse every table that has a "Market" column
        for table in soup.find_all("table"):
            header_cells = [c.get_text(" ", strip=True).lower() for c in table.find_all("th")]
            if not header_cells:
                # Some tables use <td> in first row as headers
                first_row = table.find("tr")
                if first_row:
                    header_cells = [c.get_text(" ", strip=True).lower() for c in first_row.find_all(["td", "th"])]
            if not any("market" in h or "metro" in h for h in header_cells):
                continue
            col = {h: i for i, h in enumerate(header_cells)}
            market_idx = next((col[h] for h in col if "market" in h or "metro" in h), None)
            vac_idx = next((col[h] for h in col if "vacan" in h), None)
            rent_idx = next((col[h] for h in col if "rent" in h or "asking" in h), None)
            constr_idx = next((col[h] for h in col if "construction" in h or "pipeline" in h), None)
            if market_idx is None:
                continue

            for tr in table.find_all("tr")[1:]:
                cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                if len(cells) <= market_idx:
                    continue
                metro = cells[market_idx]
                if not metro or metro.lower() in ("market", "metro", "national"):
                    continue
                rows.append({
                    "metro": metro,
                    "vacancy_rate": _parse_percent(cells[vac_idx]) if vac_idx is not None and vac_idx < len(cells) else None,
                    "avg_asking_rent_nnn": _parse_money(cells[rent_idx]) if rent_idx is not None and rent_idx < len(cells) else None,
                    "under_construction_sqft": _parse_int(cells[constr_idx]) if constr_idx is not None and constr_idx < len(cells) else None,
                    "source": "commercialedge",
                    "source_url": target,
                })
        logger.info("CommercialEdge: extracted %d metro rows", len(rows))
        return rows

    async def _fetch_cbre(self, client: httpx.AsyncClient) -> list[dict]:
        """Best-effort CBRE US Industrial Figures scrape. Returns [] if structure unrecognised."""
        resp = await client.get(CBRE_FIGURES)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        rows: list[dict] = []
        for table in soup.find_all("table"):
            headers = [c.get_text(" ", strip=True).lower() for c in table.find_all("th")]
            if not any("market" in h for h in headers):
                continue
            col = {h: i for i, h in enumerate(headers)}
            m_i = next((col[h] for h in col if "market" in h), None)
            v_i = next((col[h] for h in col if "vacancy" in h), None)
            r_i = next((col[h] for h in col if "rent" in h or "asking" in h), None)
            if m_i is None or v_i is None:
                continue
            for tr in table.find_all("tr")[1:]:
                cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                if len(cells) <= m_i:
                    continue
                rows.append({
                    "metro": cells[m_i],
                    "vacancy_rate": _parse_percent(cells[v_i]) if v_i < len(cells) else None,
                    "avg_asking_rent_nnn": _parse_money(cells[r_i]) if r_i is not None and r_i < len(cells) else None,
                    "source": "cbre",
                    "source_url": CBRE_FIGURES,
                })
        logger.info("CBRE: extracted %d metro rows", len(rows))
        return rows

    async def normalize(self, raw: list[dict]) -> list[dict]:
        today = date.today()
        # First day of current month as the "as_of" stamp
        as_of = today.replace(day=1)
        out: list[dict] = []
        for r in raw:
            metro = (r.get("metro") or "").strip()
            if not metro or len(metro) > 80:
                continue
            out.append({
                "metro": metro,
                "state": _state_for(metro),
                "market_type": _classify(metro),
                "vacancy_rate": r.get("vacancy_rate"),
                "avg_asking_rent_nnn": r.get("avg_asking_rent_nnn"),
                "avg_land_price_per_sqft": r.get("avg_land_price_per_sqft"),
                "rent_yoy_pct": r.get("rent_yoy_pct"),
                "net_absorption_sqft": r.get("net_absorption_sqft"),
                "under_construction_sqft": r.get("under_construction_sqft"),
                "source": r.get("source") or "unknown",
                "source_url": r.get("source_url"),
                "as_of_date": as_of,
            })
        return out

    async def upsert(self, session: AsyncSession, records: list[dict]) -> int:
        if not records:
            return 0
        count = 0
        for rec in records:
            await session.execute(
                text("""
                    INSERT INTO national_markets (
                        metro, state, market_type, vacancy_rate, avg_asking_rent_nnn,
                        avg_land_price_per_sqft, rent_yoy_pct, net_absorption_sqft,
                        under_construction_sqft, source, source_url, as_of_date, updated_at
                    ) VALUES (
                        :metro, :state, :market_type, :vacancy_rate, :avg_asking_rent_nnn,
                        :avg_land_price_per_sqft, :rent_yoy_pct, :net_absorption_sqft,
                        :under_construction_sqft, :source, :source_url, :as_of_date, NOW()
                    )
                    ON CONFLICT (metro, source, as_of_date) DO UPDATE SET
                        state = EXCLUDED.state,
                        market_type = EXCLUDED.market_type,
                        vacancy_rate = EXCLUDED.vacancy_rate,
                        avg_asking_rent_nnn = EXCLUDED.avg_asking_rent_nnn,
                        avg_land_price_per_sqft = EXCLUDED.avg_land_price_per_sqft,
                        rent_yoy_pct = EXCLUDED.rent_yoy_pct,
                        net_absorption_sqft = EXCLUDED.net_absorption_sqft,
                        under_construction_sqft = EXCLUDED.under_construction_sqft,
                        source_url = EXCLUDED.source_url,
                        updated_at = NOW()
                """),
                rec,
            )
            count += 1
        return count
