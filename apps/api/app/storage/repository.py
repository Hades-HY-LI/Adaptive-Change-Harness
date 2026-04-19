from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Optional
from uuid import uuid4

from app.models.schemas import (
    CodebaseDetail,
    EvidencePacket,
    FailureCase,
    RepairSkill,
    RepoProfile,
    RunCreateRequest,
    RunDetail,
    RunEvent,
    RunStatus,
    RunSummary,
    SkillStatus,
    SourceType,
    Verdict,
)


class RunRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    break_type TEXT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    seed INTEGER,
                    status TEXT NOT NULL,
                    verdict TEXT,
                    workspace_path TEXT,
                    error TEXT,
                    evidence_json TEXT,
                    codebase_id TEXT,
                    failure_case_id TEXT,
                    skill_match_id TEXT
                )
                """
            )
            self._ensure_columns(
                connection,
                "runs",
                {
                    "codebase_id": "TEXT",
                    "failure_case_id": "TEXT",
                    "skill_match_id": "TEXT",
                    "evidence_json": "TEXT",
                    "workspace_path": "TEXT",
                    "error": "TEXT",
                },
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS run_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS codebases (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    label TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    archive_path TEXT NOT NULL,
                    extracted_path TEXT NOT NULL,
                    profile_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS failure_cases (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    codebase_id TEXT NOT NULL,
                    failure_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    probe_input_json TEXT,
                    failing_command TEXT NOT NULL,
                    failing_output TEXT NOT NULL,
                    reproduction_steps_json TEXT NOT NULL,
                    suspect_files_json TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    deterministic_check_ids_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS repair_skills (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    bug_family TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    manifest_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS skill_revisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    summary TEXT NOT NULL,
                    manifest_json TEXT NOT NULL
                )
                """
            )

    def _ensure_columns(self, connection: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
        existing = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for column_name, definition in columns.items():
            if column_name in existing:
                continue
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {definition}")

    def create_run(self, payload: RunCreateRequest, model: str) -> RunSummary:
        run_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runs (
                    id, created_at, mode, break_type, provider, model, seed, status, codebase_id, failure_case_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    created_at,
                    payload.mode.value,
                    payload.break_type.value if payload.break_type else "",
                    payload.provider,
                    model,
                    payload.seed,
                    RunStatus.queued.value,
                    payload.codebase_id,
                    payload.failure_case_id,
                ),
            )
        return self.get_run(run_id)

    def update_run(
        self,
        run_id: str,
        *,
        status: Optional[RunStatus] = None,
        verdict: Optional[Verdict] = None,
        workspace_path: Optional[str] = None,
        error: Optional[str] = None,
        evidence: Optional[EvidencePacket] = None,
        skill_match_id: Optional[str] = None,
    ) -> None:
        assignments: list[str] = []
        values: list[Any] = []
        if status is not None:
            assignments.append("status = ?")
            values.append(status.value)
        if verdict is not None:
            assignments.append("verdict = ?")
            values.append(verdict.value)
        if workspace_path is not None:
            assignments.append("workspace_path = ?")
            values.append(workspace_path)
        if error is not None:
            assignments.append("error = ?")
            values.append(error)
        if evidence is not None:
            assignments.append("evidence_json = ?")
            values.append(evidence.model_dump_json())
        if skill_match_id is not None:
            assignments.append("skill_match_id = ?")
            values.append(skill_match_id)
        if not assignments:
            return
        values.append(run_id)
        with self._connect() as connection:
            connection.execute(
                f"UPDATE runs SET {', '.join(assignments)} WHERE id = ?",
                values,
            )

    def add_event(
        self,
        run_id: str,
        *,
        event_type: str,
        stage: str,
        summary: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> RunEvent:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO run_events (run_id, type, stage, summary, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    event_type,
                    stage,
                    summary,
                    created_at,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            event_id = int(cursor.lastrowid)
        return self.get_event(event_id)

    def create_codebase(
        self,
        *,
        label: str,
        source_type: SourceType,
        archive_path: str,
        extracted_path: str,
        repo_profile: RepoProfile,
    ) -> CodebaseDetail:
        codebase_id = repo_profile.id
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO codebases (id, created_at, label, source_type, archive_path, extracted_path, profile_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    codebase_id,
                    created_at,
                    label,
                    source_type.value,
                    archive_path,
                    extracted_path,
                    repo_profile.model_dump_json(),
                ),
            )
        return self.get_codebase(codebase_id)

    def get_codebase(self, codebase_id: str) -> CodebaseDetail:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM codebases WHERE id = ?", (codebase_id,)).fetchone()
        if row is None:
            raise KeyError(codebase_id)
        return self._row_to_codebase(row)

    def create_failure_case(
        self,
        *,
        codebase_id: str,
        failure_type: str,
        title: str,
        probe_input: dict[str, Any],
        failing_command: str,
        failing_output: str,
        reproduction_steps: list[str],
        suspect_files: list[str],
        severity: str,
        confidence: float,
        deterministic_check_ids: list[str],
    ) -> FailureCase:
        failure_case_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO failure_cases (
                    id, created_at, codebase_id, failure_type, title, probe_input_json, failing_command,
                    failing_output, reproduction_steps_json, suspect_files_json, severity, confidence,
                    deterministic_check_ids_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    failure_case_id,
                    created_at,
                    codebase_id,
                    failure_type,
                    title,
                    json.dumps(probe_input),
                    failing_command,
                    failing_output,
                    json.dumps(reproduction_steps),
                    json.dumps(suspect_files),
                    severity,
                    confidence,
                    json.dumps(deterministic_check_ids),
                ),
            )
        return self.get_failure_case(failure_case_id)

    def get_failure_case(self, failure_case_id: str) -> FailureCase:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM failure_cases WHERE id = ?", (failure_case_id,)).fetchone()
        if row is None:
            raise KeyError(failure_case_id)
        return self._row_to_failure_case(row)

    def list_skills(self) -> list[RepairSkill]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM repair_skills ORDER BY created_at DESC").fetchall()
        return [self._row_to_skill(row) for row in rows]

    def get_skill(self, skill_id: str) -> RepairSkill:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM repair_skills WHERE id = ?", (skill_id,)).fetchone()
        if row is None:
            raise KeyError(skill_id)
        return self._row_to_skill(row)

    def get_skill_by_slug(self, slug: str) -> RepairSkill:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM repair_skills WHERE slug = ?", (slug,)).fetchone()
        if row is None:
            raise KeyError(slug)
        return self._row_to_skill(row)

    def create_skill(self, skill: RepairSkill, *, revision_summary: str) -> RepairSkill:
        manifest = self._skill_manifest(skill)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO repair_skills (id, created_at, slug, title, bug_family, version, status, manifest_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    skill.id,
                    skill.created_at.isoformat(),
                    skill.slug,
                    skill.title,
                    skill.bug_family,
                    skill.version,
                    skill.status.value,
                    json.dumps(manifest),
                ),
            )
            connection.execute(
                """
                INSERT INTO skill_revisions (skill_id, created_at, version, summary, manifest_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    skill.id,
                    skill.created_at.isoformat(),
                    skill.version,
                    revision_summary,
                    json.dumps(manifest),
                ),
            )
        return self.get_skill(skill.id)

    def update_skill(self, skill: RepairSkill, *, revision_summary: str) -> RepairSkill:
        manifest = self._skill_manifest(skill)
        revision_created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE repair_skills
                SET title = ?, bug_family = ?, version = ?, status = ?, manifest_json = ?
                WHERE id = ?
                """,
                (
                    skill.title,
                    skill.bug_family,
                    skill.version,
                    skill.status.value,
                    json.dumps(manifest),
                    skill.id,
                ),
            )
            connection.execute(
                """
                INSERT INTO skill_revisions (skill_id, created_at, version, summary, manifest_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    skill.id,
                    revision_created_at,
                    skill.version,
                    revision_summary,
                    json.dumps(manifest),
                ),
            )
        return self.get_skill(skill.id)

    def save_skill(self, skill: RepairSkill) -> RepairSkill:
        manifest = self._skill_manifest(skill)
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE repair_skills
                SET title = ?, bug_family = ?, version = ?, status = ?, manifest_json = ?
                WHERE id = ?
                """,
                (
                    skill.title,
                    skill.bug_family,
                    skill.version,
                    skill.status.value,
                    json.dumps(manifest),
                    skill.id,
                ),
            )
        return self.get_skill(skill.id)

    def list_events(self, run_id: str, after_id: int = 0) -> list[RunEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM run_events WHERE run_id = ? AND id > ? ORDER BY id ASC",
                (run_id, after_id),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def list_runs(self) -> list[RunSummary]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM runs ORDER BY created_at DESC").fetchall()
        return [self._row_to_run_summary(row) for row in rows]

    def get_run(self, run_id: str) -> RunSummary:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return self._row_to_run_summary(row)

    def get_run_detail(self, run_id: str) -> RunDetail:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        summary = self._row_to_run_summary(row)
        events = self.list_events(run_id)
        evidence = None
        if row["evidence_json"]:
            evidence = EvidencePacket.model_validate_json(row["evidence_json"])
        return RunDetail(**summary.model_dump(), events=events, evidence=evidence)

    def get_event(self, event_id: int) -> RunEvent:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM run_events WHERE id = ?", (event_id,)).fetchone()
        if row is None:
            raise KeyError(event_id)
        return self._row_to_event(row)

    def _row_to_run_summary(self, row: sqlite3.Row) -> RunSummary:
        break_type = row["break_type"] or None
        return RunSummary.model_validate(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "mode": row["mode"],
                "break_type": break_type,
                "provider": row["provider"],
                "model": row["model"],
                "seed": row["seed"],
                "codebase_id": row["codebase_id"] if "codebase_id" in row.keys() else None,
                "failure_case_id": row["failure_case_id"] if "failure_case_id" in row.keys() else None,
                "status": row["status"],
                "verdict": row["verdict"],
                "workspace_path": row["workspace_path"],
                "error": row["error"],
            }
        )

    def _row_to_event(self, row: sqlite3.Row) -> RunEvent:
        return RunEvent.model_validate(
            {
                "id": row["id"],
                "run_id": row["run_id"],
                "type": row["type"],
                "stage": row["stage"],
                "summary": row["summary"],
                "created_at": row["created_at"],
                "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else None,
            }
        )

    def _row_to_codebase(self, row: sqlite3.Row) -> CodebaseDetail:
        profile = RepoProfile.model_validate_json(row["profile_json"])
        return CodebaseDetail.model_validate(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "label": row["label"],
                "source_type": row["source_type"],
                "archive_path": row["archive_path"],
                "extracted_path": row["extracted_path"],
                "repo_profile": profile.model_dump(mode="json"),
            }
        )

    def _row_to_failure_case(self, row: sqlite3.Row) -> FailureCase:
        return FailureCase.model_validate(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "codebase_id": row["codebase_id"],
                "failure_type": row["failure_type"],
                "title": row["title"],
                "probe_input": json.loads(row["probe_input_json"]) if row["probe_input_json"] else {},
                "failing_command": row["failing_command"],
                "failing_output": row["failing_output"],
                "reproduction_steps": json.loads(row["reproduction_steps_json"]),
                "suspect_files": json.loads(row["suspect_files_json"]),
                "severity": row["severity"],
                "confidence": row["confidence"],
                "deterministic_check_ids": json.loads(row["deterministic_check_ids_json"]),
            }
        )

    def _row_to_skill(self, row: sqlite3.Row) -> RepairSkill:
        manifest = json.loads(row["manifest_json"])
        manifest.update(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "slug": row["slug"],
                "title": row["title"],
                "bug_family": row["bug_family"],
                "version": row["version"],
                "status": row["status"] or SkillStatus.active.value,
            }
        )
        return RepairSkill.model_validate(manifest)

    def _skill_manifest(self, skill: RepairSkill) -> dict[str, Any]:
        manifest = skill.model_dump(mode="json")
        for key in ("id", "created_at", "slug", "title", "bug_family", "version", "status"):
            manifest.pop(key, None)
        return manifest
