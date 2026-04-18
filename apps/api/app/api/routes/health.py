from fastapi import APIRouter

from app.core.config import get_settings
from app.providers.registry import ProviderRegistry

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, object]:
    settings = get_settings()
    registry = ProviderRegistry(settings)
    return {
        "status": "ok",
        "service": settings.app_name,
        "configured_providers": [provider.id for provider in registry.list_providers()],
    }
