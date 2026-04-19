from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.dependencies import get_repository
from app.services.codebase_intake import CodebaseIntakeService
from app.services.repo_profiler import RepoProfiler
from app.core.config import get_settings

router = APIRouter()


@router.post("/upload")
async def upload_codebase(file: UploadFile = File(...)) -> dict[str, object]:
    repository = get_repository()
    intake_service = CodebaseIntakeService(get_settings().artifact_root, repository, RepoProfiler())
    try:
        codebase = await intake_service.ingest_zip(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"item": codebase.model_dump(mode="json")}


@router.get("/{codebase_id}")
def get_codebase(codebase_id: str) -> dict[str, object]:
    repository = get_repository()
    try:
        codebase = repository.get_codebase(codebase_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Codebase not found") from exc
    return {"item": codebase.model_dump(mode="json")}
