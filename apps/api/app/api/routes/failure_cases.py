from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.core.config import get_settings
from app.dependencies import get_repository
from app.models.schemas import FailureCaseRepairRequest, RunCreateRequest, RunMode
from app.providers.registry import ProviderRegistry
from app.services.orchestrator import HarnessOrchestrator

router = APIRouter()


@router.get("/{failure_case_id}")
def get_failure_case(failure_case_id: str) -> dict[str, object]:
    repository = get_repository()
    try:
        failure_case = repository.get_failure_case(failure_case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Failure case not found") from exc
    return {"item": failure_case.model_dump(mode="json")}


@router.post("/{failure_case_id}/repair")
def repair_failure_case(
    failure_case_id: str,
    payload: FailureCaseRepairRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, object]:
    settings = get_settings()
    repository = get_repository()
    try:
        repository.get_failure_case(failure_case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Failure case not found") from exc

    registry = ProviderRegistry(settings)
    available = {provider.id: provider for provider in registry.list_providers()}
    if payload.provider not in available:
        raise HTTPException(status_code=400, detail="Requested provider is not configured")

    run_payload = RunCreateRequest(
        mode=RunMode.replay,
        provider=payload.provider,
        model=payload.model,
        failure_case_id=failure_case_id,
    )
    run = repository.create_run(run_payload, model=payload.model or registry.default_model(payload.provider))
    orchestrator = HarnessOrchestrator(settings, repository)
    background_tasks.add_task(orchestrator.execute, run.id, run_payload)
    return {"item": run.model_dump(mode="json")}
