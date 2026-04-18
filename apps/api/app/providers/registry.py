from __future__ import annotations

from app.core.config import Settings
from app.models.schemas import ProviderInfo
from app.providers.base import RepairProvider
from app.providers.openai_provider import OpenAIProvider


class ProviderRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def list_providers(self) -> list[ProviderInfo]:
        providers: list[ProviderInfo] = []
        if self.settings.openai_api_key:
            providers.append(
                ProviderInfo(
                    id="openai",
                    label="OpenAI",
                    configured=True,
                    models=[self.settings.openai_model],
                )
            )
        return providers

    def require(self, provider_id: str) -> RepairProvider:
        if provider_id == "openai" and self.settings.openai_api_key:
            return OpenAIProvider(self.settings)
        raise ValueError(f"Provider '{provider_id}' is not configured")
