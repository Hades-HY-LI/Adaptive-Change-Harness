from fastapi import APIRouter

from app.core.config import get_settings
from app.providers.registry import ProviderRegistry

router = APIRouter()


@router.get("")
def list_providers() -> dict[str, object]:
    registry = ProviderRegistry(get_settings())
    providers = registry.list_providers()
    return {"items": [provider.model_dump() for provider in providers]}
