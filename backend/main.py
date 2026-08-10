from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import (
    deals, parcels, market, pipeline, agents, proforma, export, alerts,
    subscribers, digests,
)
from services import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    try:
        yield
    finally:
        scheduler.stop()


app = FastAPI(title="FlexScout API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers under /api
app.include_router(deals.router, prefix="/api")
app.include_router(parcels.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(proforma.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(subscribers.router, prefix="/api")
app.include_router(digests.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
