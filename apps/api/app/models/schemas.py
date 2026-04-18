from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class RunMode(str, Enum):
    inject = "inject"
    verify = "verify"


class BreakType(str, Enum):
    logic_regression = "logic_regression"
    contract_violation = "contract_violation"
    invariant_violation = "invariant_violation"


class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    repairing = "repairing"
    completed = "completed"
    failed = "failed"


class Verdict(str, Enum):
    safe = "safe"
    unsafe = "unsafe"
    needs_review = "needs_review"


class RunCreateRequest(BaseModel):
    mode: RunMode = RunMode.inject
    break_type: BreakType
    provider: str = "openai"
    model: Optional[str] = None
    seed: Optional[int] = Field(default=7, ge=0)


class ProviderInfo(BaseModel):
    id: str
    label: str
    configured: bool
    models: list[str]


class RunEvent(BaseModel):
    id: int
    run_id: str
    type: str
    stage: str
    summary: str
    created_at: datetime
    metadata: Optional[dict[str, Any]] = None


class EvaluatorResult(BaseModel):
    name: str
    passed: bool
    summary: str
    details: str
    artifact_path: Optional[str] = None


class EvidencePacket(BaseModel):
    failed_evaluators_before: list[EvaluatorResult] = Field(default_factory=list)
    passed_evaluators_after: list[EvaluatorResult] = Field(default_factory=list)
    root_cause_summary: str = ""
    patch_summary: str = ""
    merge_confidence: str = "needs_review"
    artifact_manifest: dict[str, str] = Field(default_factory=dict)


class RunSummary(BaseModel):
    id: str
    created_at: datetime
    mode: RunMode
    break_type: BreakType
    provider: str
    model: str
    seed: Optional[int] = None
    status: RunStatus
    verdict: Optional[Verdict] = None
    workspace_path: Optional[str] = None
    error: Optional[str] = None


class RunDetail(RunSummary):
    events: list[RunEvent] = Field(default_factory=list)
    evidence: Optional[EvidencePacket] = None
