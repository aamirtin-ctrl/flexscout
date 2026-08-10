from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session, verify_api_key

router = APIRouter(prefix="/alerts", tags=["alerts"], dependencies=[Depends(verify_api_key)])

# In-memory alerts store for MVP (no DB table in Phase 1 schema)
_alerts: dict[int, dict] = {}
_next_id = 1


@router.get("")
async def list_alerts():
    return {"alerts": list(_alerts.values())}


@router.post("")
async def create_alert(body: dict):
    global _next_id
    alert = {
        "id": _next_id,
        "name": body["name"],
        "filters": body.get("filters", {}),
        "frequency": body.get("frequency", "daily"),
        "email": body.get("email"),
        "active": True,
    }
    _alerts[_next_id] = alert
    _next_id += 1
    return alert


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int):
    if alert_id not in _alerts:
        raise HTTPException(404, "Alert not found")
    del _alerts[alert_id]
    return {"ok": True}
