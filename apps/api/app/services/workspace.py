from __future__ import annotations

from pathlib import Path
import shutil


class WorkspaceService:
    def __init__(self, artifact_root: Path, demo_repo_root: Path) -> None:
        self.artifact_root = artifact_root
        self.demo_repo_root = demo_repo_root

    def create(self, run_id: str) -> Path:
        return self.create_from_demo(run_id)

    def create_from_demo(self, run_id: str) -> Path:
        return self._copy_workspace(run_id, self.demo_repo_root)

    def create_from_codebase(self, run_id: str, source_root: Path) -> Path:
        return self._copy_workspace(run_id, source_root)

    def _copy_workspace(self, run_id: str, source_root: Path) -> Path:
        workspace_root = self.artifact_root / "workspaces"
        workspace_root.mkdir(parents=True, exist_ok=True)
        destination = workspace_root / run_id
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source_root, destination)
        return destination
