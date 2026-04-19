from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class RunMode(str, Enum):
    discover = "discover"
    inject = "inject"
    replay = "replay"


class BreakType(str, Enum):
    logic_regression = "logic_regression"
    contract_violation = "contract_violation"
    invariant_violation = "invariant_violation"


class SourceType(str, Enum):
    zip_upload = "zip_upload"
    demo_repo = "demo_repo"


class SkillStatus(str, Enum):
    active = "active"
    draft = "draft"
    deprecated = "deprecated"


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
    no_reproducible_failure_found = "no_reproducible_failure_found"


class RunCreateRequest(BaseModel):
    mode: RunMode = RunMode.inject
    break_type: Optional[BreakType] = None
    provider: str = "openai"
    model: Optional[str] = None
    seed: Optional[int] = Field(default=7, ge=0)
    codebase_id: Optional[str] = None
    failure_case_id: Optional[str] = None


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


class RepoProfile(BaseModel):
    id: str
    source_type: SourceType
    workspace_path: str
    language: str = "unknown"
    framework: str = "unknown"
    package_manager: Optional[str] = None
    install_command: Optional[str] = None
    test_command: Optional[str] = None
    source_dirs: list[str] = Field(default_factory=list)
    test_dirs: list[str] = Field(default_factory=list)
    entrypoints: list[str] = Field(default_factory=list)
    risk_areas: list[str] = Field(default_factory=list)


class CodebaseSummary(BaseModel):
    id: str
    created_at: datetime
    label: str
    source_type: SourceType
    archive_path: str
    extracted_path: str


class CodebaseDetail(CodebaseSummary):
    repo_profile: RepoProfile


class FailureCase(BaseModel):
    id: str
    created_at: datetime
    codebase_id: str
    failure_type: str
    title: str
    probe_input: dict[str, Any] = Field(default_factory=dict)
    failing_command: str
    failing_output: str
    reproduction_steps: list[str] = Field(default_factory=list)
    suspect_files: list[str] = Field(default_factory=list)
    severity: str = "medium"
    confidence: float = 0.0
    deterministic_check_ids: list[str] = Field(default_factory=list)


class FailureCaseRepairRequest(BaseModel):
    provider: str = "openai"
    model: Optional[str] = None


class RepairSkill(BaseModel):
    id: str
    created_at: datetime
    slug: str
    title: str
    bug_family: str
    version: int = 1
    status: SkillStatus = SkillStatus.active
    trigger_signals: list[str] = Field(default_factory=list)
    applicability_rules: list[str] = Field(default_factory=list)
    required_context: list[str] = Field(default_factory=list)
    investigation_flow: list[str] = Field(default_factory=list)
    repair_strategy: list[str] = Field(default_factory=list)
    verification_recipe: list[str] = Field(default_factory=list)
    exemplar_failure_case_ids: list[str] = Field(default_factory=list)
    created_from_failure_case_id: Optional[str] = None
    last_updated_from_failure_case_id: Optional[str] = None
    usage_count: int = 0
    success_count: int = 0


class SkillDecision(BaseModel):
    matched_skill_id: Optional[str] = None
    matched_skill_title: Optional[str] = None
    action: str = "none"
    rationale: str = ""


class ReplayComparison(BaseModel):
    failure_case_id: str
    original_failing_command: str
    original_failure_type: str
    original_failure_excerpt: str = ""
    reproduced_before_repair: bool = False
    reproduced_after_repair: bool = False
    latest_repro_excerpt: str = ""
    validation_commands: list[str] = Field(default_factory=list)


class EvidencePacket(BaseModel):
    failed_evaluators_before: list[EvaluatorResult] = Field(default_factory=list)
    passed_evaluators_after: list[EvaluatorResult] = Field(default_factory=list)
    root_cause_summary: str = ""
    patch_summary: str = ""
    merge_confidence: str = "needs_review"
    artifact_manifest: dict[str, str] = Field(default_factory=dict)
    repo_profile_summary: str = ""
    failure_case_summary: str = ""
    skill_decision: Optional[SkillDecision] = None
    replay_comparison: Optional[ReplayComparison] = None


class RunSummary(BaseModel):
    id: str
    created_at: datetime
    mode: RunMode
    break_type: Optional[BreakType] = None
    provider: str
    model: str
    seed: Optional[int] = None
    codebase_id: Optional[str] = None
    failure_case_id: Optional[str] = None
    status: RunStatus
    verdict: Optional[Verdict] = None
    workspace_path: Optional[str] = None
    error: Optional[str] = None


class RunDetail(RunSummary):
    events: list[RunEvent] = Field(default_factory=list)
    evidence: Optional[EvidencePacket] = None
