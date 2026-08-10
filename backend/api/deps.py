from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.session import get_db


async def verify_api_key(x_api_key: str = Header(None)) -> str:
    if settings.ENVIRONMENT == "development":
        return "dev"
    if not x_api_key or x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


async def get_session(session: AsyncSession = Depends(get_db)) -> AsyncSession:
    return session
