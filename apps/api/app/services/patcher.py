from __future__ import annotations

from pathlib import Path

from app.providers.base import PatchOperation, RepairProposal


class PatchService:
    def apply(self, workspace: Path, proposal: RepairProposal) -> list[str]:
        changed_files: list[str] = []
        for patch in proposal.patches:
            changed_files.append(self._apply_operation(workspace, patch))
        return changed_files

    def _apply_operation(self, workspace: Path, patch: PatchOperation) -> str:
        target = (workspace / patch.file_path).resolve()
        if workspace.resolve() not in target.parents and target != workspace.resolve():
            raise ValueError(f"Patch path escapes workspace: {patch.file_path}")
        content = target.read_text()
        if patch.search not in content:
            raise ValueError(f"Patch search text not found in {patch.file_path}")
        target.write_text(content.replace(patch.search, patch.replace, 1))
        return patch.file_path
