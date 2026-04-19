from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from uuid import uuid4

from app.models.schemas import FailureCase, RepairSkill, RepoProfile, SkillDecision
from app.providers.base import RepairProposal
from app.storage.repository import RunRepository


@dataclass
class SkillMatch:
    skill: RepairSkill
    rationale: str
    score: int


class SkillLibraryService:
    def __init__(self, skill_assets_root: Path, repository: RunRepository) -> None:
        self.skill_assets_root = skill_assets_root
        self.repository = repository
        self._ensure_layout()

    def _ensure_layout(self) -> None:
        for child in ("manifests", "skills", "revisions", "indexes"):
            (self.skill_assets_root / child).mkdir(parents=True, exist_ok=True)

    def list_skills(self) -> list[RepairSkill]:
        return self.repository.list_skills()

    def get_skill(self, skill_id: str) -> RepairSkill:
        return self.repository.get_skill(skill_id)

    def match_failure_case(self, failure_case: FailureCase) -> SkillMatch | None:
        best_match: SkillMatch | None = None
        failure_signals = {failure_case.failure_type, failure_case.severity}
        failure_signals.update(Path(path).name.lower() for path in failure_case.suspect_files)

        for skill in self.list_skills():
            score = 0
            reasons: list[str] = []
            if skill.bug_family == failure_case.failure_type:
                score += 5
                reasons.append("bug family matched exactly")
            overlap = sorted(failure_signals & {signal.lower() for signal in skill.trigger_signals})
            if overlap:
                score += len(overlap) * 2
                reasons.append(f"trigger overlap: {', '.join(overlap)}")
            if not reasons:
                continue
            match = SkillMatch(skill=skill, rationale="; ".join(reasons), score=score)
            if best_match is None or match.score > best_match.score:
                best_match = match

        return best_match

    def record_validated_repair(
        self,
        *,
        failure_case: FailureCase,
        repo_profile: RepoProfile,
        proposal: RepairProposal,
        matched_skill: RepairSkill | None,
    ) -> SkillDecision:
        if matched_skill is None:
            skill = self._build_new_skill(failure_case, repo_profile, proposal)
            stored = self.repository.create_skill(skill, revision_summary=proposal.patch_summary)
            self._write_skill_assets(stored, revision_summary=proposal.patch_summary, write_revision=True)
            return SkillDecision(
                matched_skill_id=stored.id,
                matched_skill_title=stored.title,
                action="created",
                rationale="Validated repair produced a new repair skill asset.",
            )

        updated_trigger_signals = self._merge_unique(
            matched_skill.trigger_signals,
            [failure_case.failure_type, failure_case.severity, *[Path(path).name for path in failure_case.suspect_files]],
        )
        updated_required_context = self._merge_unique(matched_skill.required_context, failure_case.suspect_files)
        updated_repair_strategy = self._merge_unique(matched_skill.repair_strategy, [proposal.patch_summary])
        updated_verification_recipe = self._merge_unique(
            matched_skill.verification_recipe,
            [*failure_case.reproduction_steps, repo_profile.test_command or ""],
        )
        exemplar_ids = list(dict.fromkeys([*matched_skill.exemplar_failure_case_ids, failure_case.id]))
        introduces_new_revision = any(
            [
                updated_trigger_signals != matched_skill.trigger_signals,
                updated_required_context != matched_skill.required_context,
                updated_repair_strategy != matched_skill.repair_strategy,
                updated_verification_recipe != matched_skill.verification_recipe,
                exemplar_ids != matched_skill.exemplar_failure_case_ids,
            ]
        )

        if not introduces_new_revision:
            reused_skill = matched_skill.model_copy(
                update={
                    "usage_count": matched_skill.usage_count + 1,
                    "success_count": matched_skill.success_count + 1,
                }
            )
            stored = self.repository.save_skill(reused_skill)
            self._write_skill_assets(stored, revision_summary=proposal.patch_summary, write_revision=False)
            return SkillDecision(
                matched_skill_id=stored.id,
                matched_skill_title=stored.title,
                action="reused",
                rationale="Matched skill guidance was sufficient without creating a new revision.",
            )

        updated_skill = matched_skill.model_copy(
            update={
                "version": matched_skill.version + 1,
                "last_updated_from_failure_case_id": failure_case.id,
                "usage_count": matched_skill.usage_count + 1,
                "success_count": matched_skill.success_count + 1,
                "exemplar_failure_case_ids": exemplar_ids,
                "trigger_signals": updated_trigger_signals,
                "required_context": updated_required_context,
                "repair_strategy": updated_repair_strategy,
                "verification_recipe": updated_verification_recipe,
            }
        )
        stored = self.repository.update_skill(updated_skill, revision_summary=proposal.patch_summary)
        self._write_skill_assets(stored, revision_summary=proposal.patch_summary, write_revision=True)
        return SkillDecision(
            matched_skill_id=stored.id,
            matched_skill_title=stored.title,
            action="updated",
            rationale="Validated repair updated the matched repair skill with a new revision.",
        )

    def _build_new_skill(
        self,
        failure_case: FailureCase,
        repo_profile: RepoProfile,
        proposal: RepairProposal,
    ) -> RepairSkill:
        created_at = datetime.now(timezone.utc)
        title = f"{failure_case.title} repair"
        slug = self._unique_slug(self._slugify(failure_case.failure_type or failure_case.title))
        suspect_files = list(dict.fromkeys(failure_case.suspect_files))
        verification_recipe = [*failure_case.reproduction_steps]
        if repo_profile.test_command:
            verification_recipe.append(repo_profile.test_command)
        return RepairSkill(
            id=str(uuid4()),
            created_at=created_at,
            slug=slug,
            title=title,
            bug_family=failure_case.failure_type,
            trigger_signals=self._merge_unique(
                [],
                [failure_case.failure_type, failure_case.severity, *[Path(path).name for path in suspect_files]],
            ),
            applicability_rules=[
                f"Use when the saved repro `{failure_case.failing_command}` fails with similar output.",
                f"Repo profile: {repo_profile.language}/{repo_profile.framework}.",
            ],
            required_context=suspect_files,
            investigation_flow=self._merge_unique([], [failure_case.failing_command, *failure_case.reproduction_steps]),
            repair_strategy=[proposal.patch_summary],
            verification_recipe=self._merge_unique([], verification_recipe),
            exemplar_failure_case_ids=[failure_case.id],
            created_from_failure_case_id=failure_case.id,
            last_updated_from_failure_case_id=failure_case.id,
            usage_count=1,
            success_count=1,
        )

    def _write_skill_assets(self, skill: RepairSkill, *, revision_summary: str, write_revision: bool) -> None:
        manifest_path = self.skill_assets_root / "manifests" / f"{skill.id}.json"
        skill_path = self.skill_assets_root / "skills" / f"{skill.slug}.json"
        revision_dir = self.skill_assets_root / "revisions" / skill.id
        revision_dir.mkdir(parents=True, exist_ok=True)
        revision_path = revision_dir / f"v{skill.version}.json"
        index_path = self.skill_assets_root / "indexes" / "skills.json"

        manifest_payload = {
            "id": skill.id,
            "slug": skill.slug,
            "title": skill.title,
            "bug_family": skill.bug_family,
            "version": skill.version,
            "status": skill.status.value,
            "trigger_signals": skill.trigger_signals,
            "last_updated_from_failure_case_id": skill.last_updated_from_failure_case_id,
        }
        revision_payload = {
            "summary": revision_summary,
            "skill": skill.model_dump(mode="json"),
        }

        manifest_path.write_text(json.dumps(manifest_payload, indent=2) + "\n")
        skill_path.write_text(json.dumps(skill.model_dump(mode="json"), indent=2) + "\n")
        if write_revision:
            revision_path.write_text(json.dumps(revision_payload, indent=2) + "\n")

        index_payload = [
            {
                "id": existing.id,
                "slug": existing.slug,
                "title": existing.title,
                "bug_family": existing.bug_family,
                "version": existing.version,
                "status": existing.status.value,
            }
            for existing in self.list_skills()
        ]
        index_path.write_text(json.dumps(index_payload, indent=2) + "\n")

    def _merge_unique(self, existing: list[str], additions: list[str]) -> list[str]:
        merged = [item for item in existing if item]
        seen = {item.lower() for item in merged}
        for item in additions:
            if not item:
                continue
            lowered = item.lower()
            if lowered in seen:
                continue
            merged.append(item)
            seen.add(lowered)
        return merged

    def _slugify(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "repair-skill"

    def _unique_slug(self, base_slug: str) -> str:
        try:
            self.repository.get_skill_by_slug(base_slug)
        except KeyError:
            return base_slug
        return f"{base_slug}-{uuid4().hex[:8]}"
