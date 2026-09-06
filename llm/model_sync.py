from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config import (
    ModelProviderSettings,
    backup_model_provider_settings,
    list_model_provider_settings,
    rollback_model_provider_settings,
    update_model_provider_models,
)
from llm.openai_compatible import OpenAICompatibleClient, fetch_available_models


@dataclass(frozen=True)
class ModelRefreshResult:
    provider: ModelProviderSettings
    models: tuple[str, ...]
    current_model: str
    current_model_available: bool
    validation_error: str | None = None


def _find_provider(provider_name: str, path: str | Path | None) -> ModelProviderSettings:
    for provider in list_model_provider_settings(path):
        if provider.name == provider_name:
            return provider
    raise ValueError(f"Unknown model provider: {provider_name}")


def refresh_model_provider(
    provider_name: str,
    *,
    path: str | Path | None = None,
    timeout: float = 30.0,
) -> ModelRefreshResult:
    provider = _find_provider(provider_name, path)
    models = fetch_available_models(provider, timeout=timeout)
    current_model_available = provider.model_name in models
    validation_error: str | None = None
    if current_model_available:
        try:
            OpenAICompatibleClient(provider, timeout=timeout).complete(
                [{"role": "user", "content": "Reply with OK."}]
            )
        except Exception as exc:
            current_model_available = False
            validation_error = str(exc)

    backup_model_provider_settings(path)
    updated = update_model_provider_models(provider_name, models, path)
    return ModelRefreshResult(updated, models, updated.model_name, current_model_available, validation_error)


__all__ = [
    "ModelRefreshResult",
    "refresh_model_provider",
    "rollback_model_provider_settings",
]
