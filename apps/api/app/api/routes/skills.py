from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.dependencies import get_repository
from app.services.skill_library import SkillLibraryService

router = APIRouter()


@router.get("")
def list_skills() -> dict[str, object]:
    repository = get_repository()
    service = SkillLibraryService(get_settings().skill_assets_root, repository)
    skills = service.list_skills()
    return {"items": [skill.model_dump(mode="json") for skill in skills]}


@router.get("/{skill_id}")
def get_skill(skill_id: str) -> dict[str, object]:
    repository = get_repository()
    service = SkillLibraryService(get_settings().skill_assets_root, repository)
    try:
        skill = service.get_skill(skill_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Skill not found") from exc
    return {"item": skill.model_dump(mode="json")}
