from __future__ import annotations

from pathlib import Path
import shutil


class WorkspaceService:
    def __init__(self, artifact_root: Path, demo_repo_root: Path) -> None:
        self.artifact_root = artifact_root
        self.demo_repo_root = demo_repo_root

    def create(self, run_id: str) -> Path:
        workspace_root = self.artifact_root / "workspaces"
        workspace_root.mkdir(parents=True, exist_ok=True)
        destination = workspace_root / run_id
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(self.demo_repo_root, destination)
        return destination
