from __future__ import annotations

import io
import logging
from datetime import datetime

import httpx
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agents.base import BaseAgent

logger = logging.getLogger(__name__)

TAD_BULK_URL = "https://www.tad.org/data-download"

TARGET_LAND_USE_CODES = ["C1", "C2", "F1", "F2", "C3"]

FIELD_MAP = {
    "GEO_ID": "apn",
    "OWNER": "owner_name",
    "SITUS": "address",
    "LAND_VAL": "land_value",
    "IMPRV_VAL": "imprv_value",
    "LAND_SQFT": "land_sqft",
    "STATE_CD": "land_use_code",
    "DEED_DT": "deed_date",
    "TAX_STATUS": "tax_status",
    "DELINQ_AMT": "delinquency_amt",
    "LATITUDE": "lat",
    "LONGITUDE": "lng",
}


def parse_date(val) -> datetime | None:
    if pd.isna(val) or not val:
        return None
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None


class TADAgent(BaseAgent):
    name = "tad"
    schedule = "0 3 * * 0"  # Sunday 3am

    async def fetch(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.get(TAD_BULK_URL)
            resp.raise_for_status()

        df = pd.read_csv(io.StringIO(resp.text), dtype=str, low_memory=False)
        # Rename columns via FIELD_MAP where they exist
        rename = {k: v for k, v in FIELD_MAP.items() if k in df.columns}
        df = df.rename(columns=rename)

        if "land_use_code" in df.columns:
            df = df[df["land_use_code"].isin(TARGET_LAND_USE_CODES)]
        return df.to_dict("records")

    async def normalize(self, raw: list[dict]) -> list[dict]:
        records = []
        for row in raw:
            try:
                land_sqft = float(row.get("land_sqft") or 0)
                imprv_value = int(float(row.get("imprv_value") or 0))
                land_value = int(float(row.get("land_value") or 0))
                lat = float(row["lat"]) if row.get("lat") else None
                lng = float(row["lng"]) if row.get("lng") else None

                record = {
                    "apn": str(row.get("apn", "")).strip(),
                    "county": "tarrant",
                    "address": str(row.get("address", "")).strip() or None,
                    "lat": lat,
                    "lng": lng,
                    "acreage": round(land_sqft / 43560, 3) if land_sqft else None,
                    "land_use_code": str(row.get("land_use_code", "")).strip() or None,
                    "owner_name": str(row.get("owner_name", "")).strip() or None,
                    "owner_since": parse_date(row.get("deed_date")),
                    "land_value": land_value,
                    "imprv_value": imprv_value,
                    "is_vacant": imprv_value < 5000,
                    "is_delinquent": str(row.get("tax_status", "")).strip().upper() != "CURRENT",
                    "delinquency_amt": int(float(row.get("delinquency_amt") or 0)) or None,
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
