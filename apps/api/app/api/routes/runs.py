from __future__ import annotations

import json
import time

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.dependencies import get_repository
from app.models.schemas import RunCreateRequest
from app.providers.registry import ProviderRegistry
from app.services.orchestrator import HarnessOrchestrator

router = APIRouter()


@router.get("")
def list_runs() -> dict[str, object]:
    repository = get_repository()
    return {"items": [run.model_dump(mode="json") for run in repository.list_runs()]}


@router.post("")
def create_run(payload: RunCreateRequest, background_tasks: BackgroundTasks) -> dict[str, object]:
    settings = get_settings()
    repository = get_repository()
    registry = ProviderRegistry(settings)
    available = {provider.id: provider for provider in registry.list_providers()}
    if payload.provider not in available:
        raise HTTPException(status_code=400, detail="Requested provider is not configured")

    model = payload.model or settings.openai_model
    run = repository.create_run(payload, model=model)
    orchestrator = HarnessOrchestrator(settings, repository)
    background_tasks.add_task(orchestrator.execute, run.id, payload)
    return {"item": run.model_dump(mode="json")}


@router.get("/{run_id}")
def get_run(run_id: str) -> dict[str, object]:
    repository = get_repository()
    try:
        detail = repository.get_run_detail(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    return {"item": detail.model_dump(mode="json")}


@router.get("/{run_id}/events")
def stream_run_events(run_id: str) -> StreamingResponse:
    repository = get_repository()

    def event_stream():
        last_seen = 0
        terminal_statuses = {"completed", "failed"}
        while True:
            events = repository.list_events(run_id, after_id=last_seen)
            for event in events:
                last_seen = event.id
                yield f"event: {event.type}\ndata: {json.dumps(event.model_dump(mode='json'))}\n\n"
            try:
                run = repository.get_run(run_id)
            except KeyError:
                yield "event: error\ndata: {\"message\": \"Run not found\"}\n\n"
                break
            if run.status.value in terminal_statuses and not events:
                yield f"event: complete\ndata: {json.dumps(run.model_dump(mode='json'))}\n\n"
                break
            time.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
