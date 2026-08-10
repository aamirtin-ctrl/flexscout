from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from db import async_session, AgentRun

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    name: str = "base"
    schedule: str = "0 0 * * *"

    def __init__(self):
        self.logger = logging.getLogger(f"agent.{self.name}")

    @abstractmethod
    async def fetch(self) -> list[dict]:
        """Pull raw data from source."""
        ...

    @abstractmethod
    async def normalize(self, raw: list[dict]) -> list[dict]:
        """Map raw data to internal schema."""
        ...

    @abstractmethod
    async def upsert(self, session: AsyncSession, records: list[dict]) -> int:
        """Write to DB with ON CONFLICT DO UPDATE. Returns count upserted."""
        ...

    async def run(self) -> None:
        started_at = datetime.utcnow()
        errors: list[str] = []
        fetched = 0
        upserted = 0

        try:
            self.logger.info(f"[{self.name}] Starting fetch...")
            raw = await self.fetch()
            fetched = len(raw)
            self.logger.info(f"[{self.name}] Fetched {fetched} records")

            records = await self.normalize(raw)
            self.logger.info(f"[{self.name}] Normalized {len(records)} records")

            async with async_session() as session:
                upserted = await self.upsert(session, records)
                await session.commit()

            self.logger.info(f"[{self.name}] Upserted {upserted} records")
            status = "success"
        except Exception as e:
            self.logger.error(f"[{self.name}] Failed: {e}", exc_info=True)
            errors.append(str(e))
            status = "failed"

        await self.log_run(status, fetched, upserted, errors, started_at)

    async def log_run(
        self, status: str, fetched: int, upserted: int, errors: list[str], started_at: datetime
    ) -> None:
        async with async_session() as session:
            await session.execute(
                insert(AgentRun).values(
                    agent_name=self.name,
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    status=status,
                    records_fetched=fetched,
                    records_upserted=upserted,
                    error_messages=errors,
                )
            )
            await session.commit()
