from fastapi import APIRouter

from app.api.routes import codebases, failure_cases, health, providers, runs, skills

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(codebases.router, prefix="/codebases", tags=["codebases"])
api_router.include_router(failure_cases.router, prefix="/failure-cases", tags=["failure-cases"])
api_router.include_router(providers.router, prefix="/providers", tags=["providers"])
api_router.include_router(runs.router, prefix="/runs", tags=["runs"])
api_router.include_router(skills.router, prefix="/skills", tags=["skills"])
