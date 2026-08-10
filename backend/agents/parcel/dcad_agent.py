from __future__ import annotations

import io
import logging
from datetime import datetime

import httpx
import pandas as pd
from geoalchemy2 import WKTElement
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agents.base import BaseAgent

logger = logging.getLogger(__name__)

DCAD_BULK_URL = "https://www.dallascad.org/AcctDetailRes.aspx"

TARGET_LAND_USE_CODES = ["C1", "C2", "F1", "F2", "C3"]


def parse_date(val) -> datetime | None:
    if pd.isna(val) or not val:
        return None
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None


class DCADAgent(BaseAgent):
    name = "dcad"
    schedule = "0 2 * * 0"  # Sunday 2am

    async def fetch(self) -> list[dict]:
        """Download Dallas CAD bulk CSV. Returns list of row dicts."""
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.get(DCAD_BULK_URL)
            resp.raise_for_status()

        df = pd.read_csv(io.StringIO(resp.text), dtype=str, low_memory=False)
        # Filter to target land use codes
        if "STATE_CODE" in df.columns:
            df = df[df["STATE_CODE"].isin(TARGET_LAND_USE_CODES)]
        return df.to_dict("records")

    async def normalize(self, raw: list[dict]) -> list[dict]:
        records = []
        for row in raw:
            try:
                land_sqft = float(row.get("LAND_SQFT") or 0)
                imprv_value = int(float(row.get("IMPRV_VALUE") or 0))
                land_value = int(float(row.get("LAND_VALUE") or 0))
                lat = float(row["LATITUDE"]) if row.get("LATITUDE") else None
                lng = float(row["LONGITUDE"]) if row.get("LONGITUDE") else None

                record = {
                    "apn": row.get("ACCOUNT_NUM", "").strip(),
                    "county": "dallas",
                    "address": row.get("SITUS_ADDRESS", "").strip() or None,
                    "lat": lat,
                    "lng": lng,
                    "acreage": round(land_sqft / 43560, 3) if land_sqft else None,
                    "land_use_code": row.get("STATE_CODE", "").strip() or None,
                    "owner_name": row.get("OWNER_NAME", "").strip() or None,
                    "owner_since": parse_date(row.get("DEED_DATE")),
                    "land_value": land_value,
                    "imprv_value": imprv_value,
                    "is_vacant": imprv_value < 5000,
                    "is_delinquent": row.get("TAX_STATUS", "").strip().upper() != "CURRENT",
                    "delinquency_amt": int(float(row.get("DELINQUENT_AMT") or 0)) or None,
                }

                if record["apn"]:
                    records.append(record)
            except Exception as e:
                logger.warning(f"Skipping row: {e}")
        return records

    async def upsert(self, session: AsyncSession, records: list[dict]) -> int:
        if not records:
            return 0

        upserted = 0
        for rec in records:
            geom_val = f"SRID=4326;POINT({rec['lng']} {rec['lat']})" if rec.get("lat") and rec.get("lng") else None

            await session.execute(
                text("""
                    INSERT INTO parcels (apn, county, address, lat, lng, geom, acreage, land_use_code,
                        owner_name, owner_since, land_value, imprv_value, is_vacant, is_delinquent,
                        delinquency_amt, updated_at)
                    VALUES (:apn, :county, :address, :lat, :lng,
                        ST_GeomFromEWKT(:geom),
                        :acreage, :land_use_code, :owner_name, :owner_since, :land_value, :imprv_value,
                        :is_vacant, :is_delinquent, :delinquency_amt, NOW())
                    ON CONFLICT (apn, county) DO UPDATE SET
                        address = EXCLUDED.address,
                        lat = EXCLUDED.lat,
                        lng = EXCLUDED.lng,
                        geom = EXCLUDED.geom,
                        acreage = EXCLUDED.acreage,
                        land_use_code = EXCLUDED.land_use_code,
                        owner_name = EXCLUDED.owner_name,
                        owner_since = EXCLUDED.owner_since,
                        land_value = EXCLUDED.land_value,
                        imprv_value = EXCLUDED.imprv_value,
                        is_vacant = EXCLUDED.is_vacant,
                        is_delinquent = EXCLUDED.is_delinquent,
                        delinquency_amt = EXCLUDED.delinquency_amt,
                        updated_at = NOW()
                """),
                {**rec, "geom": geom_val},
            )
            upserted += 1

        return upserted
