import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session, verify_api_key

router = APIRouter(prefix="/agents", tags=["agents"], dependencies=[Depends(verify_api_key)])

AGENT_MAP = {
    "dcad": "agents.parcel.dcad_agent:DCADAgent",
    "tad": "agents.parcel.tad_agent:TADAgent",
    "zoning_dallas": "agents.zoning.dallas_zoning_agent:DallasZoningAgent",
    "comp_engine": "agents.enrichment.comp_engine:CompEngine",
    "deal_scoring": "agents.scoring.deal_scoring_agent:DealScoringAgent",
    "national_market": "agents.market.national_market_agent:NationalMarketAgent",
    "market_digest": "agents.alerts.digest_agent:MarketDigestAgent",
}


@router.get("/status")
async def agent_status(session: AsyncSession = Depends(get_session)):
    result = await session.execute(text("""
        SELECT DISTINCT ON (agent_name)
            agent_name, started_at, completed_at, status, records_fetched, records_upserted, error_messages
        FROM agent_runs
        ORDER BY agent_name, started_at DESC
    """))
    return {
        "agents": [
            {
                "name": r["agent_name"],
                "last_run": r["started_at"].isoformat() if r["started_at"] else None,
                "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
                "status": r["status"],
                "records_fetched": r["records_fetched"],
                "records_upserted": r["records_upserted"],
                "errors": r["error_messages"] or [],
            }
            for r in result.mappings().all()
        ]
    }


@router.post("/{name}/trigger")
async def trigger_agent(name: str):
    if name not in AGENT_MAP:
        raise HTTPException(404, f"Unknown agent: {name}")

    module_path, class_name = AGENT_MAP[name].rsplit(":", 1)
    import importlib
    module = importlib.import_module(module_path)
    agent_class = getattr(module, class_name)
    agent = agent_class()

    # Run in background
    asyncio.create_task(agent.run())

    return {"ok": True, "message": f"Agent '{name}' triggered"}
