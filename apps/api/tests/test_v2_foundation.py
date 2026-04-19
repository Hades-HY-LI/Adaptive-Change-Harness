from __future__ import annotations

from pathlib import Path
import time
import zipfile

from fastapi.testclient import TestClient
import pytest

@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    artifact_root = tmp_path / "artifacts"
    skill_assets_root = tmp_path / "skill_assets"
    monkeypatch.setenv("ARTIFACT_ROOT", str(artifact_root))
    monkeypatch.setenv("DATABASE_PATH", str(artifact_root / "test.sqlite3"))
    monkeypatch.setenv("SKILL_ASSETS_ROOT", str(skill_assets_root))
    monkeypatch.setenv("FAKE_PROVIDER_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.core.config import get_settings
    from app.dependencies import get_repository
    from app.main import create_app

    get_settings.cache_clear()
    get_repository.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    get_repository.cache_clear()
    get_settings.cache_clear()


def test_upload_codebase_builds_repo_profile(client: TestClient, tmp_path: Path) -> None:
    archive_path = _build_python_service_zip(tmp_path, failing=False)
    response = client.post(
        "/api/v1/codebases/upload",
        files={"file": ("sample-service.zip", archive_path.read_bytes(), "application/zip")},
    )
    assert response.status_code == 200
    payload = response.json()["item"]
    assert payload["source_type"] == "zip_upload"
    assert payload["repo_profile"]["language"] == "python"
    assert payload["repo_profile"]["framework"] == "fastapi"
    assert payload["repo_profile"]["test_command"] == "python -m pytest"


def test_discover_run_can_report_no_reproducible_failure(client: TestClient, tmp_path: Path) -> None:
    archive_path = _build_python_service_zip(tmp_path, failing=False)
    upload_response = client.post(
        "/api/v1/codebases/upload",
        files={"file": ("sample-service.zip", archive_path.read_bytes(), "application/zip")},
    )
    codebase_id = upload_response.json()["item"]["id"]
    create_response = client.post(
        "/api/v1/runs",
        json={"mode": "discover", "codebase_id": codebase_id, "provider": "openai", "model": "gpt-5"},
    )
    assert create_response.status_code == 200
    run_id = create_response.json()["item"]["id"]

    detail = _wait_for_run_completion(client, run_id)
    assert detail["status"] == "completed"
    assert detail["verdict"] == "no_reproducible_failure_found"
    event_types = [event["type"] for event in detail["events"]]
    assert "codebase_profiled" in event_types
    profile_event = next(event for event in detail["events"] if event["type"] == "codebase_profiled")
    assert profile_event["metadata"]["framework"] == "fastapi"
    assert profile_event["metadata"]["test_command"] == "python -m pytest"
    baseline_event = next(
        event
        for event in detail["events"]
        if event["stage"] == "discover" and event["type"] == "evaluation_passed"
    )
    assert baseline_event["metadata"]["result"]["name"] == "baseline_tests"
    assert "passed" in baseline_event["metadata"]["result"]["summary"].lower()
    assert "verdict_ready" in event_types


def test_discover_run_can_capture_probe_discovered_failure(client: TestClient, tmp_path: Path) -> None:
    archive_path = _build_probe_target_zip(tmp_path)
    upload_response = client.post(
        "/api/v1/codebases/upload",
        files={"file": ("probe-target.zip", archive_path.read_bytes(), "application/zip")},
    )
    codebase_id = upload_response.json()["item"]["id"]
    create_response = client.post(
        "/api/v1/runs",
        json={"mode": "discover", "codebase_id": codebase_id, "provider": "openai", "model": "gpt-5"},
    )
    assert create_response.status_code == 200
    run_id = create_response.json()["item"]["id"]

    detail = _wait_for_run_completion(client, run_id)
    assert detail["status"] == "completed"
    assert detail["verdict"] == "unsafe"
    event_types = [event["type"] for event in detail["events"]]
    assert event_types == [
        "run_created",
        "codebase_profiled",
        "discovery_started",
        "evaluation_failed",
        "probe_executed",
        "failure_case_captured",
        "verdict_ready",
    ]
    baseline_event = next(
        event
        for event in detail["events"]
        if event["stage"] == "discover" and event["type"] == "evaluation_failed"
    )
    assert baseline_event["metadata"]["result"]["name"] == "baseline_tests"
    assert baseline_event["metadata"]["result"]["passed"] is True
    probe_event = next(event for event in detail["events"] if event["type"] == "probe_executed")
    assert probe_event["metadata"]["probe_id"] == "negative_total_quote"
    assert probe_event["metadata"]["title"] == "Negative total quote probe"
    assert probe_event["metadata"]["passed"] is False
    assert probe_event["metadata"]["severity"] == "high"
    assert probe_event["metadata"]["confidence"] == pytest.approx(0.95)
    assert probe_event["metadata"]["command"] == "python .harness/probes/negative_total_quote_probe.py"
    assert "negative total detected" in probe_event["metadata"]["details_excerpt"]
    assert "negative total detected" in probe_event["metadata"]["details"]
    captured_event = next(event for event in detail["events"] if event["type"] == "failure_case_captured")
    assert captured_event["summary"] == "Negative total quote probe"
    assert captured_event["metadata"]["title"] == "Negative total quote probe"
    assert captured_event["metadata"]["failure_type"] == "negative_total_quote"
    assert captured_event["metadata"]["failing_command"] == "python .harness/probes/negative_total_quote_probe.py"
    assert "negative total detected" in captured_event["metadata"]["failing_output"]
    assert captured_event["metadata"]["reproduction_steps"] == [
        "python .harness/probes/negative_total_quote_probe.py"
    ]
    assert captured_event["metadata"]["suspect_files"] == ["app/services/pricing.py"]
    assert captured_event["metadata"]["severity"] == "high"
    assert captured_event["metadata"]["confidence"] == pytest.approx(0.95)
    assert captured_event["metadata"]["deterministic_check_ids"] == ["negative_total_quote"]
    failure_case_id = detail["evidence"]["artifact_manifest"]["failure_case_id"]
    failure_case_response = client.get(f"/api/v1/failure-cases/{failure_case_id}")
    assert failure_case_response.status_code == 200
    failure_case = failure_case_response.json()["item"]
    assert failure_case["failure_type"] == "negative_total_quote"
    assert "negative total detected" in failure_case["failing_output"]
    assert failure_case["deterministic_check_ids"] == ["negative_total_quote"]


def test_list_skills_returns_empty_collection_in_first_slice(client: TestClient) -> None:
    response = client.get("/api/v1/skills")
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_list_providers_includes_fake_and_openai_when_enabled(client: TestClient) -> None:
    response = client.get("/api/v1/providers")
    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "fake",
                "label": "Deterministic Demo",
                "configured": True,
                "models": ["deterministic-repair-v1"],
            },
            {
                "id": "openai",
                "label": "OpenAI",
                "configured": True,
                "models": ["gpt-5"],
            },
        ]
    }


def test_failure_case_repair_prompt_skips_directory_context_entries(tmp_path: Path) -> None:
    from app.models.schemas import EvaluatorResult, FailureCase, RepoProfile, SourceType
    from app.services.prompts import build_failure_case_repair_prompt

    workspace = tmp_path / "workspace"
    app_dir = workspace / "app"
    service_file = app_dir / "services" / "pricing.py"
    service_file.parent.mkdir(parents=True, exist_ok=True)
    service_file.write_text("def build_quote(request):\n    return {'total_cents': -1}\n")

    failure_case = FailureCase(
        id="failure-1",
        created_at="2026-04-19T08:00:00Z",
        codebase_id="codebase-1",
        failure_type="negative_total_quote",
        title="Negative total quote probe",
        failing_command="python .harness/probes/negative_total_quote_probe.py",
        failing_output="negative total detected",
        reproduction_steps=["python .harness/probes/negative_total_quote_probe.py"],
        suspect_files=["app", "app/services/pricing.py"],
        deterministic_check_ids=["negative_total_quote"],
    )
    repo_profile = RepoProfile(
        id="codebase-1",
        source_type=SourceType.zip_upload,
        workspace_path=str(workspace),
        language="python",
        framework="fastapi",
        source_dirs=["app"],
        entrypoints=["app/main.py"],
    )
    repro_result = EvaluatorResult(
        name="saved_repro",
        passed=False,
        summary="Saved failure case reproduced successfully.",
        details="negative total detected",
    )

    prompt = build_failure_case_repair_prompt(workspace, failure_case, repo_profile, repro_result)

    assert "FILE: app\n```python" not in prompt
    assert "FILE: app/services/pricing.py" in prompt


def test_failure_case_repair_uses_saved_repro_and_creates_skill_asset(
    client: TestClient,
    tmp_path: Path,
) -> None:
    archive_path = _build_probe_target_zip(tmp_path)
    upload_response = client.post(
        "/api/v1/codebases/upload",
        files={"file": ("probe-target.zip", archive_path.read_bytes(), "application/zip")},
    )
    codebase_id = upload_response.json()["item"]["id"]
    discover_response = client.post(
        "/api/v1/runs",
        json={"mode": "discover", "codebase_id": codebase_id, "provider": "openai", "model": "gpt-5"},
    )
    run_id = discover_response.json()["item"]["id"]
    discover_detail = _wait_for_run_completion(client, run_id)
    failure_case_id = discover_detail["evidence"]["artifact_manifest"]["failure_case_id"]

    repair_response = client.post(
        f"/api/v1/failure-cases/{failure_case_id}/repair",
        json={"provider": "fake", "model": "deterministic-repair-v1"},
    )
    assert repair_response.status_code == 200
    repair_run_id = repair_response.json()["item"]["id"]

    repair_detail = _wait_for_run_completion(client, repair_run_id)
    assert repair_detail["mode"] == "replay"
    assert repair_detail["provider"] == "fake"
    assert repair_detail["model"] == "deterministic-repair-v1"
    assert repair_detail["status"] == "completed"
    assert repair_detail["verdict"] == "safe"
    assert repair_detail["evidence"]["skill_decision"]["action"] == "created"
    assert repair_detail["evidence"]["replay_comparison"]["reproduced_before_repair"] is True
    assert repair_detail["evidence"]["replay_comparison"]["reproduced_after_repair"] is False
    assert "saved_repro" in [result["name"] for result in repair_detail["evidence"]["passed_evaluators_after"]]

    skill_response = client.get("/api/v1/skills")
    assert skill_response.status_code == 200
    skills = skill_response.json()["items"]
    assert len(skills) == 1
    skill = skills[0]
    assert skill["bug_family"] == "negative_total_quote"

    skill_assets_root = tmp_path / "skill_assets"
    assert (skill_assets_root / "skills" / f"{skill['slug']}.json").exists()
    assert (skill_assets_root / "manifests" / f"{skill['id']}.json").exists()
    assert (skill_assets_root / "revisions" / skill["id"] / "v1.json").exists()
    index_payload = (skill_assets_root / "indexes" / "skills.json").read_text()
    assert "negative_total_quote" in index_payload


def test_replay_reuses_existing_skill_without_new_revision(
    client: TestClient,
    tmp_path: Path,
) -> None:
    archive_path = _build_probe_target_zip(tmp_path)
    upload_response = client.post(
        "/api/v1/codebases/upload",
        files={"file": ("probe-target.zip", archive_path.read_bytes(), "application/zip")},
    )
    codebase_id = upload_response.json()["item"]["id"]
    discover_response = client.post(
        "/api/v1/runs",
        json={"mode": "discover", "codebase_id": codebase_id, "provider": "openai", "model": "gpt-5"},
    )
    discover_run_id = discover_response.json()["item"]["id"]
    discover_detail = _wait_for_run_completion(client, discover_run_id)
    failure_case_id = discover_detail["evidence"]["artifact_manifest"]["failure_case_id"]

    first_repair = client.post(
        f"/api/v1/failure-cases/{failure_case_id}/repair",
        json={"provider": "fake", "model": "deterministic-repair-v1"},
    )
    first_repair_detail = _wait_for_run_completion(client, first_repair.json()["item"]["id"])
    assert first_repair_detail["evidence"]["skill_decision"]["action"] == "created"

    second_repair = client.post(
        f"/api/v1/failure-cases/{failure_case_id}/repair",
        json={"provider": "fake", "model": "deterministic-repair-v1"},
    )
    second_repair_detail = _wait_for_run_completion(client, second_repair.json()["item"]["id"])
    assert second_repair_detail["verdict"] == "safe"
    assert second_repair_detail["evidence"]["skill_decision"]["action"] == "reused"
    assert second_repair_detail["evidence"]["skill_decision"]["matched_skill_id"] is not None
    event_types = [event["type"] for event in second_repair_detail["events"]]
    assert "skill_matched" in event_types
    assert "skill_reused" in event_types
    assert second_repair_detail["evidence"]["replay_comparison"]["validation_commands"] == [
        "python .harness/probes/negative_total_quote_probe.py",
        "python -m pytest",
    ]

    skills = client.get("/api/v1/skills").json()["items"]
    assert len(skills) == 1
    skill = skills[0]
    assert skill["version"] == 1
    assert skill["usage_count"] == 2
    assert skill["success_count"] == 2

    revision_dir = tmp_path / "skill_assets" / "revisions" / skill["id"]
    assert sorted(path.name for path in revision_dir.iterdir()) == ["v1.json"]


def _wait_for_run_completion(client: TestClient, run_id: str) -> dict[str, object]:
    for _ in range(20):
        response = client.get(f"/api/v1/runs/{run_id}")
        assert response.status_code == 200
        payload = response.json()["item"]
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.1)
    raise AssertionError("Run did not complete in time")


def _build_python_service_zip(tmp_path: Path, *, failing: bool) -> Path:
    repo_root = tmp_path / "sample_service"
    app_dir = repo_root / "app"
    tests_dir = repo_root / "tests"
    app_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)
    (repo_root / "pyproject.toml").write_text(
        """
[project]
name = "sample-service"
version = "0.1.0"
"""
    )
    (app_dir / "main.py").write_text(
        """
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}
"""
    )
    test_body = "def test_truth():\n    assert 1 == 0\n" if failing else "def test_truth():\n    assert 1 == 1\n"
    (tests_dir / "test_smoke.py").write_text(test_body)

    archive_path = tmp_path / "sample-service.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for file_path in repo_root.rglob("*"):
            archive.write(file_path, file_path.relative_to(repo_root))
    return archive_path


def _build_probe_target_zip(tmp_path: Path) -> Path:
    repo_root = tmp_path / "probe_target"
    app_dir = repo_root / "app"
    services_dir = app_dir / "services"
    tests_dir = repo_root / "tests"
    services_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)
    (repo_root / "pyproject.toml").write_text(
        """
[project]
name = "probe-target"
version = "0.1.0"
"""
    )
    (app_dir / "__init__.py").write_text("")
    (services_dir / "__init__.py").write_text("")
    (app_dir / "main.py").write_text(
        """
from fastapi import FastAPI

from app.services.pricing import build_quote

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/quote")
def quote(request: dict):
    return build_quote(request)
"""
    )
    (services_dir / "pricing.py").write_text(
        """
PLAN_PRICES = {"starter": 1500, "pro": 4500, "enterprise": 9000}
DISCOUNTS = {"WELCOME10": ("percent", 10), "MEGAFLAT": ("fixed", 5000)}


def build_quote(request: dict) -> dict:
    subtotal = PLAN_PRICES[request["plan_code"]] * request.get("seats", 1)
    discount_code = request.get("discount_code")
    discount_cents = 0
    if discount_code:
        discount_type, value = DISCOUNTS[discount_code]
        if discount_type == "percent":
            discount_cents = int(subtotal * (value / 100))
        else:
            discount_cents = value
    taxable_total = subtotal - discount_cents
    tax_cents = int(taxable_total * 0.10)
    return {
        "plan_code": request["plan_code"],
        "subtotal_cents": subtotal,
        "discount_cents": discount_cents,
        "tax_cents": tax_cents,
        "total_cents": taxable_total + tax_cents,
    }
"""
    )
    (tests_dir / "test_smoke.py").write_text(
        """
from app.services.pricing import build_quote


def test_normal_quote_is_positive():
    payload = build_quote({"plan_code": "starter", "seats": 1, "discount_code": "WELCOME10"})
    assert payload["total_cents"] > 0
"""
    )

    archive_path = tmp_path / "probe-target.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for file_path in repo_root.rglob("*"):
            archive.write(file_path, file_path.relative_to(repo_root))
    return archive_path
