from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PatchOperation:
    file_path: str
    search: str
    replace: str


@dataclass
class RepairProposal:
    root_cause_summary: str
    patch_summary: str
    merge_confidence: str
    patches: list[PatchOperation]


class ProviderError(RuntimeError):
    pass


class RepairProvider:
    id: str

    def generate_repair(self, *, model: str, prompt: str) -> RepairProposal:
        raise NotImplementedError
