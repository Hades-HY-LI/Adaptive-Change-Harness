from fastapi import APIRouter

from app.api.routes import health, providers, runs

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(providers.router, prefix="/providers", tags=["providers"])
api_router.include_router(runs.router, prefix="/runs", tags=["runs"])
