import logging
import tempfile

import geopandas as gpd
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agents.base import BaseAgent

logger = logging.getLogger(__name__)

DALLAS_ZONING_URL = "https://gis.dallascityhall.com/shapefileExport/zoning.geojson"
CODE_FIELD = "ZONEDIST"
DESC_FIELD = "ZONE_DESC"

FLEX_COMPATIBLE_CODES = ["IR", "LI", "IM", "CS", "M-1", "M-2", "BC", "BP"]


class DallasZoningAgent(BaseAgent):
    name = "zoning_dallas"
    schedule = "0 1 1 * *"  # 1st of month 1am

    async def fetch(self) -> list[dict]:
        """Download GeoJSON zoning polygons."""
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(DALLAS_ZONING_URL)
            resp.raise_for_status()

        # Write to temp file for geopandas
        with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False, mode="w") as f:
            f.write(resp.text)
            tmp_path = f.name

        gdf = gpd.read_file(tmp_path)
        gdf = gdf.to_crs(epsg=4326)  # ensure WGS84

        records = []
        for _, row in gdf.iterrows():
            records.append({
                "code": row.get(CODE_FIELD, ""),
                "description": row.get(DESC_FIELD, ""),
                "geom_wkt": row.geometry.wkt if row.geometry else None,
            })
        return records

    async def normalize(self, raw: list[dict]) -> list[dict]:
        return [r for r in raw if r.get("geom_wkt") and r.get("code")]

    async def upsert(self, session: AsyncSession, records: list[dict]) -> int:
        # Create temp table for zoning polygons
        await session.execute(text("""
            CREATE TEMP TABLE IF NOT EXISTS zoning_polygons (
                code VARCHAR(20),
                description TEXT,
                geom GEOMETRY(MultiPolygon, 4326)
            ) ON COMMIT DROP
        """))

        for rec in records:
            try:
                await session.execute(
                    text("""
                        INSERT INTO zoning_polygons (code, description, geom)
                        VALUES (:code, :description, ST_Multi(ST_GeomFromText(:geom_wkt, 4326)))
                    """),
                    rec,
                )
            except Exception as e:
                logger.warning(f"Skipping zoning polygon: {e}")

        # Spatial join: update parcels with zoning info
        result = await session.execute(text("""
            UPDATE parcels p
            SET zoning_code = z.code,
                zoning_desc = z.description,
                updated_at = NOW()
            FROM zoning_polygons z
            WHERE ST_Within(p.geom, z.geom)
              AND p.county = 'dallas'
        """))

        return result.rowcount
