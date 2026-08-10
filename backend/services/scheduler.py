"""APScheduler wiring. Registers agent cron jobs on app startup.

Each agent exposes a `schedule` (cron string) and a `name`. Jobs are idempotent —
if a digest run overlaps the previous one it will just insert a new row keyed on
generated_at. If the scheduler is disabled via env (FLEXSCOUT_SCHEDULER=off),
the app still starts but no background work runs.
"""
from __future__ import annotations

import logging
import os
from typing import Iterable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _agent_classes() -> Iterable[type]:
    # Imported lazily so circular imports don't bite on module load
    from agents.market.national_market_agent import NationalMarketAgent
    from agents.alerts.digest_agent import MarketDigestAgent
    return [NationalMarketAgent, MarketDigestAgent]


def _run_agent(agent_cls):
    """APScheduler callable — instantiates a fresh agent and awaits its run."""
    async def runner():
        try:
            agent = agent_cls()
            await agent.run()
        except Exception as e:
            logger.exception("Scheduled agent %s crashed: %s", agent_cls.__name__, e)
    return runner


def start() -> AsyncIOScheduler | None:
    global _scheduler
    if os.getenv("FLEXSCOUT_SCHEDULER", "on").lower() == "off":
        logger.info("Scheduler disabled via FLEXSCOUT_SCHEDULER=off")
        return None
    if _scheduler is not None:
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone="UTC")
    for cls in _agent_classes():
        try:
            trigger = CronTrigger.from_crontab(getattr(cls, "schedule"))
            _scheduler.add_job(
                _run_agent(cls),
                trigger=trigger,
                id=cls.name,
                name=cls.name,
                replace_existing=True,
                misfire_grace_time=3600,
            )
            logger.info("Registered %s on %s", cls.name, cls.schedule)
        except Exception as e:
            logger.exception("Failed to register %s: %s", cls.__name__, e)

    _scheduler.start()
    return _scheduler


def stop() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
