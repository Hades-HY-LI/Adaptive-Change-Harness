from __future__ import annotations

import json

import httpx

from app.core.config import Settings
from app.providers.base import PatchOperation, ProviderError, RepairProposal, RepairProvider


class OpenAIProvider(RepairProvider):
    id = "openai"

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ProviderError("OPENAI_API_KEY is not configured")
        self._api_key = settings.openai_api_key
        self._timeout = settings.request_timeout_seconds

    def generate_repair(self, *, model: str, prompt: str) -> RepairProposal:
        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": [
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt}],
                    }
                ],
            },
            timeout=self._timeout,
        )
        if response.status_code >= 400:
            raise ProviderError(f"OpenAI request failed: {response.text}")
        text = self._extract_text(response.json())
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"OpenAI returned invalid JSON: {text}") from exc

        patches = [
            PatchOperation(
                file_path=item["file_path"],
                search=item["search"],
                replace=item["replace"],
            )
            for item in payload.get("patches", [])
        ]
        return RepairProposal(
            root_cause_summary=payload.get("root_cause_summary", "No root cause summary returned."),
            patch_summary=payload.get("patch_summary", "No patch summary returned."),
            merge_confidence=payload.get("merge_confidence", "needs_review"),
            patches=patches,
        )

    def _extract_text(self, payload: dict) -> str:
        if isinstance(payload.get("output_text"), str):
            return payload["output_text"]
        chunks: list[str] = []
        for item in payload.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        if not chunks:
            raise ProviderError(f"No text content found in response: {payload}")
        return "\n".join(chunks)
