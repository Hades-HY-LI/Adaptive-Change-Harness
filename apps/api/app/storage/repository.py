from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Optional
from uuid import uuid4

from app.models.schemas import EvidencePacket, RunCreateRequest, RunDetail, RunEvent, RunStatus, RunSummary, Verdict


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
                    break_type TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    seed INTEGER,
                    status TEXT NOT NULL,
                    verdict TEXT,
                    workspace_path TEXT,
                    error TEXT,
                    evidence_json TEXT
                )
                """
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

    def create_run(self, payload: RunCreateRequest, model: str) -> RunSummary:
        run_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runs (id, created_at, mode, break_type, provider, model, seed, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    created_at,
                    payload.mode.value,
                    payload.break_type.value,
                    payload.provider,
                    model,
                    payload.seed,
                    RunStatus.queued.value,
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

    def get_event(self, event_id: int) -> RunEvent:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM run_events WHERE id = ?", (event_id,)).fetchone()
        if row is None:
            raise KeyError(event_id)
        return self._row_to_event(row)

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

    def _row_to_run_summary(self, row: sqlite3.Row) -> RunSummary:
        return RunSummary.model_validate(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "mode": row["mode"],
                "break_type": row["break_type"],
                "provider": row["provider"],
                "model": row["model"],
                "seed": row["seed"],
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
