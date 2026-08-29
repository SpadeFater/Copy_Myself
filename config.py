from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_APP_NAME = "Copy_Myself"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_MODEL_NAME = "local-runtime"
LEGACY_MODEL_PLACEHOLDER = "placeholder-local"
CURRENT_MODEL_ENV_VARS = (
    "COPY_MYSELF_ACTIVE_MODEL",
    "COPY_MYSELF_CURRENT_MODEL",
    "COPY_MYSELF_MODEL",
    "COPY_MYSELF_MODEL_NAME",
)
CONFIG_DIR_ENV = "COPY_MYSELF_CONFIG_DIR"
MODEL_SETTINGS_PATH_ENV = "COPY_MYSELF_MODEL_SETTINGS_PATH"
MCP_SERVICES_PATH_ENV = "COPY_MYSELF_MCP_SERVICES_PATH"


def _clean_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_placeholder_model(value: str | None) -> bool:
    text = _clean_text(value)
    return text is None or text.lower() in {LEGACY_MODEL_PLACEHOLDER, "placeholder"}


def _first_env_value(env: Mapping[str, str], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        candidate = _clean_text(env.get(key))
        if candidate is not None:
            return candidate
    return None


def _config_dir() -> Path:
    custom_dir = _clean_text(os.getenv(CONFIG_DIR_ENV))
    if custom_dir is not None:
        return Path(custom_dir).expanduser()
    return Path.home() / ".copy_myself"


def default_model_settings_path() -> Path:
    override = _clean_text(os.getenv(MODEL_SETTINGS_PATH_ENV))
    if override is not None:
        return Path(override).expanduser()
    return _config_dir() / "models.json"


def default_mcp_services_path() -> Path:
    override = _clean_text(os.getenv(MCP_SERVICES_PATH_ENV))
    if override is not None:
        return Path(override).expanduser()
    return _config_dir() / "mcp_services.json"


def _ensure_parent_directory(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _coerce_string_sequence(values: object) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (str(values),)
    if isinstance(values, Iterable):
        return tuple(str(value) for value in values if _clean_text(value) is not None)
    return ()


def _coerce_unique_strings(values: object) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in _coerce_string_sequence(values):
        text = _clean_text(value)
        if text is None or text in seen:
            continue
        cleaned.append(text)
        seen.add(text)
    return tuple(cleaned)


def _coerce_string_mapping(values: object) -> dict[str, str]:
    if values is None or not isinstance(values, Mapping):
        return {}
    return {
        str(key).strip(): str(value).strip()
        for key, value in values.items()
        if _clean_text(key) is not None and _clean_text(value) is not None
    }


def _read_json_records(path: Path) -> list[Mapping[str, Any]]:
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list.")
    return [item for item in data if isinstance(item, Mapping)]


def _write_json_records(path: Path, payload: list[dict[str, object]]) -> None:
    _ensure_parent_directory(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass(frozen=True)
class ModelProviderSettings:
    name: str
    base_url: str
    model_name: str
    api_key: str = ""
    provider: str = "openai-compatible"
    headers: dict[str, str] = field(default_factory=dict)
    available_models: tuple[str, ...] = ()
    enabled: bool = True

    def __post_init__(self) -> None:
        name = _clean_text(self.name)
        base_url = _clean_text(self.base_url)
        model_name = _clean_text(self.model_name)
        if name is None:
            raise ValueError("Model provider name is required.")
        if base_url is None:
            raise ValueError("Model provider URL is required.")
        if model_name is None:
            raise ValueError("Model name is required.")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "base_url", base_url)
        object.__setattr__(self, "model_name", model_name)
        object.__setattr__(self, "api_key", _clean_text(self.api_key) or "")
        object.__setattr__(self, "provider", _clean_text(self.provider) or "openai-compatible")
        object.__setattr__(self, "headers", _coerce_string_mapping(self.headers))
        object.__setattr__(self, "available_models", _coerce_unique_strings(self.available_models))
        object.__setattr__(self, "enabled", bool(self.enabled))

    @property
    def current_model(self) -> str:
        return self.model_name

    def to_record(self) -> dict[str, object]:
        return {
            "name": self.name,
            "base_url": self.base_url,
            "model_name": self.model_name,
            "api_key": self.api_key,
            "provider": self.provider,
            "headers": dict(self.headers),
            "available_models": list(self.available_models),
            "enabled": self.enabled,
        }

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> ModelProviderSettings:
        return cls(
            name=data.get("name", ""),
            base_url=data.get("base_url", data.get("url", "")),
            model_name=data.get("model_name", data.get("model", "")),
            api_key=data.get("api_key", ""),
            provider=data.get("provider", "openai-compatible"),
            headers=_coerce_string_mapping(data.get("headers")),
            available_models=_coerce_unique_strings(data.get("available_models")),
            enabled=bool(data.get("enabled", True)),
        )


@dataclass(frozen=True)
class ModelSettings:
    current_model: str = DEFAULT_MODEL_NAME
    source: str = "default"
    configured_model: str = LEGACY_MODEL_PLACEHOLDER
    providers: tuple[ModelProviderSettings, ...] = ()

    @property
    def name(self) -> str:
        return self.current_model


@dataclass(frozen=True)
class McpServiceSettings:
    name: str
    service_id: str = ""
    endpoint: str = ""
    transport: str = "stdio"
    command: str = ""
    args: tuple[str, ...] = ()
    headers: dict[str, str] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    timeout_seconds: float = 30.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        name = _clean_text(self.name)
        if name is None:
            raise ValueError("MCP service name is required.")

        object.__setattr__(self, "name", name)
        service_id = _clean_text(self.service_id)
        if service_id is None:
            service_id = "-".join(part for part in "".join(character.lower() if character.isalnum() else " " for character in name).split()) or "service"
        if any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for character in service_id):
            raise ValueError("MCP service_id must use lowercase letters, numbers, '-' or '_'.")
        object.__setattr__(self, "service_id", service_id)
        object.__setattr__(self, "endpoint", _clean_text(self.endpoint) or "")
        transport = _clean_text(self.transport) or "stdio"
        object.__setattr__(self, "transport", "streamable_http" if transport == "http" else transport)
        object.__setattr__(self, "command", _clean_text(self.command) or "")
        object.__setattr__(self, "args", _coerce_string_sequence(self.args))
        object.__setattr__(self, "headers", _coerce_string_mapping(self.headers))
        object.__setattr__(self, "env", _coerce_string_mapping(self.env))
        object.__setattr__(self, "enabled", bool(self.enabled))
        object.__setattr__(self, "timeout_seconds", float(self.timeout_seconds))
        object.__setattr__(self, "metadata", dict(self.metadata) if isinstance(self.metadata, Mapping) else {})

    def to_record(self) -> dict[str, object]:
        return {
            "name": self.name,
            "service_id": self.service_id,
            "endpoint": self.endpoint,
            "transport": self.transport,
            "command": self.command,
            "args": list(self.args),
            "headers": dict(self.headers),
            "env": dict(self.env),
            "enabled": self.enabled,
            "timeout_seconds": self.timeout_seconds,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> McpServiceSettings:
        if data.get("service_id") == "builtin":
            raise ValueError("MCP service_id 'builtin' is reserved.")
        return cls(
            name=data.get("name", ""),
            service_id=data.get("service_id", ""),
            endpoint=data.get("endpoint", data.get("url", "")),
            transport=data.get("transport", "stdio"),
            command=data.get("command", ""),
            args=_coerce_string_sequence(data.get("args")),
            headers=_coerce_string_mapping(data.get("headers")),
            env=_coerce_string_mapping(data.get("env")),
            enabled=bool(data.get("enabled", True)),
            timeout_seconds=float(data.get("timeout_seconds", 30.0)),
            metadata=data.get("metadata", {}),
        )


@dataclass(frozen=True)
class Settings:
    app_name: str = DEFAULT_APP_NAME
    log_level: str = DEFAULT_LOG_LEVEL
    model: ModelSettings = field(default_factory=ModelSettings)
    mcp_services: tuple[McpServiceSettings, ...] = field(default_factory=tuple)

    @property
    def model_name(self) -> str:
        return self.model.current_model

    @property
    def configured_model_name(self) -> str:
        return self.model.configured_model


def list_model_provider_settings(path: str | Path | None = None) -> tuple[ModelProviderSettings, ...]:
    store_path = Path(path) if path is not None else default_model_settings_path()
    return tuple(ModelProviderSettings.from_record(item) for item in _read_json_records(store_path))


def save_model_provider_settings(
    providers: Iterable[ModelProviderSettings | Mapping[str, Any]],
    path: str | Path | None = None,
) -> tuple[ModelProviderSettings, ...]:
    store_path = Path(path) if path is not None else default_model_settings_path()
    normalized = tuple(
        provider if isinstance(provider, ModelProviderSettings) else ModelProviderSettings.from_record(provider)
        for provider in providers
    )
    _write_json_records(store_path, [provider.to_record() for provider in normalized])
    return normalized


def import_model_provider_settings(
    provider: ModelProviderSettings | Mapping[str, Any],
    path: str | Path | None = None,
) -> ModelProviderSettings:
    imported = provider if isinstance(provider, ModelProviderSettings) else ModelProviderSettings.from_record(provider)
    store_path = Path(path) if path is not None else default_model_settings_path()
    existing = list(list_model_provider_settings(store_path))
    updated: list[ModelProviderSettings] = []
    replaced = False
    for item in existing:
        if item.name == imported.name:
            updated.append(imported)
            replaced = True
        else:
            updated.append(item)
    if not replaced:
        updated.append(imported)
    save_model_provider_settings(updated, store_path)
    return imported


def import_model_provider_setting(
    *,
    name: str,
    base_url: str,
    model_name: str,
    api_key: str = "",
    provider: str = "openai-compatible",
    headers: Mapping[str, str] | None = None,
    available_models: Iterable[str] = (),
    enabled: bool = True,
) -> ModelProviderSettings:
    return import_model_provider_settings(
        ModelProviderSettings(
            name=name,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            provider=provider,
            headers=dict(headers or {}),
            available_models=tuple(available_models),
            enabled=enabled,
        )
    )


def delete_model_provider_setting(
    provider_name: str,
    path: str | Path | None = None,
) -> tuple[ModelProviderSettings, ...]:
    clean_provider_name = _clean_text(provider_name)
    if clean_provider_name is None:
        raise ValueError("Model provider name is required.")

    store_path = Path(path) if path is not None else default_model_settings_path()
    providers = [
        provider
        for provider in list_model_provider_settings(store_path)
        if provider.name != clean_provider_name
    ]
    return save_model_provider_settings(providers, store_path)


def select_model_provider_model(
    provider_name: str,
    model_name: str,
    path: str | Path | None = None,
) -> ModelProviderSettings:
    clean_provider_name = _clean_text(provider_name)
    clean_model_name = _clean_text(model_name)
    if clean_provider_name is None:
        raise ValueError("Model provider name is required.")
    if clean_model_name is None:
        raise ValueError("Model name is required.")

    store_path = Path(path) if path is not None else default_model_settings_path()
    providers = list(list_model_provider_settings(store_path))
    selected: ModelProviderSettings | None = None
    remaining: list[ModelProviderSettings] = []
    for provider in providers:
        if provider.name == clean_provider_name:
            selected = ModelProviderSettings(
                name=provider.name,
                base_url=provider.base_url,
                model_name=clean_model_name,
                api_key=provider.api_key,
                provider=provider.provider,
                headers=provider.headers,
                available_models=provider.available_models,
                enabled=provider.enabled,
            )
        else:
            remaining.append(provider)
    if selected is None:
        raise ValueError(f"Unknown model provider: {clean_provider_name}")
    save_model_provider_settings([selected, *remaining], store_path)
    return selected


def load_mcp_service_settings(path: str | Path | None = None) -> tuple[McpServiceSettings, ...]:
    store_path = Path(path) if path is not None else default_mcp_services_path()
    records = _read_json_records(store_path)
    services = tuple(McpServiceSettings.from_record(item) for item in records)
    _validate_mcp_services(services)
    if records and any(not _clean_text(item.get("service_id")) for item in records):
        _write_json_records(store_path, [service.to_record() for service in services])
    return services


def list_mcp_service_settings(path: str | Path | None = None) -> tuple[McpServiceSettings, ...]:
    return load_mcp_service_settings(path)


def save_mcp_service_settings(
    services: Iterable[McpServiceSettings | Mapping[str, Any]],
    path: str | Path | None = None,
) -> tuple[McpServiceSettings, ...]:
    store_path = Path(path) if path is not None else default_mcp_services_path()
    normalized = tuple(
        service if isinstance(service, McpServiceSettings) else McpServiceSettings.from_record(service)
        for service in services
    )
    _validate_mcp_services(normalized)
    _write_json_records(store_path, [service.to_record() for service in normalized])
    return normalized


def _validate_mcp_services(services: Iterable[McpServiceSettings]) -> None:
    service_ids: set[str] = set()
    for service in services:
        if service.service_id == "builtin":
            raise ValueError("MCP service_id 'builtin' is reserved.")
        if service.service_id in service_ids:
            raise ValueError(f"Duplicate MCP service_id: {service.service_id}")
        service_ids.add(service.service_id)


def import_mcp_service_settings(
    service: McpServiceSettings | Mapping[str, Any],
    path: str | Path | None = None,
) -> McpServiceSettings:
    imported = service if isinstance(service, McpServiceSettings) else McpServiceSettings.from_record(service)
    store_path = Path(path) if path is not None else default_mcp_services_path()
    existing = list(load_mcp_service_settings(store_path))
    updated: list[McpServiceSettings] = []
    replaced = False
    for item in existing:
        if item.service_id == imported.service_id:
            updated.append(imported)
            replaced = True
        else:
            updated.append(item)
    if not replaced:
        updated.append(imported)
    save_mcp_service_settings(updated, store_path)
    return imported


def import_mcp_service_setting(
    value: str,
    *,
    name: str | None = None,
    transport: str = "stdio",
    command: str = "",
    args: Iterable[str] = (),
    headers: Mapping[str, str] | None = None,
    enabled: bool = True,
    service_id: str = "",
) -> McpServiceSettings:
    clean_value = _clean_text(value) or ""
    clean_name = _clean_text(name) or clean_value or "External MCP"
    return import_mcp_service_settings(
        McpServiceSettings(
            name=clean_name,
            service_id=service_id,
            endpoint=clean_value,
            transport=transport,
            command=command,
            args=tuple(args),
            headers=dict(headers or {}),
            enabled=enabled,
        )
    )


def resolve_current_model_name(
    env: Mapping[str, str] | None = None,
    providers: Iterable[ModelProviderSettings] = (),
) -> str:
    source = env if env is not None else os.environ
    assert source is not None
    for key in CURRENT_MODEL_ENV_VARS:
        candidate = _clean_text(source.get(key))
        if candidate is not None and not _is_placeholder_model(candidate):
            return candidate
    for provider in providers:
        if provider.enabled:
            return provider.model_name
    return DEFAULT_MODEL_NAME


def resolve_configured_model_name(env: Mapping[str, str] | None = None) -> str:
    source = env if env is not None else os.environ
    assert source is not None
    configured = _first_env_value(source, CURRENT_MODEL_ENV_VARS)
    return configured or LEGACY_MODEL_PLACEHOLDER


def _resolve_model_settings(
    env: Mapping[str, str] | None = None,
    model_settings_path: str | Path | None = None,
) -> ModelSettings:
    source = env if env is not None else os.environ
    assert source is not None
    providers = list_model_provider_settings(model_settings_path)
    configured = _first_env_value(source, CURRENT_MODEL_ENV_VARS)
    current_model = resolve_current_model_name(source, providers)
    if configured is not None and not _is_placeholder_model(configured):
        source_name = next(
            (key for key in CURRENT_MODEL_ENV_VARS if _clean_text(source.get(key)) == current_model),
            "environment",
        )
    elif providers and current_model != DEFAULT_MODEL_NAME:
        source_name = "imported-model"
    else:
        source_name = "default"
    return ModelSettings(
        current_model=current_model,
        source=source_name,
        configured_model=configured or LEGACY_MODEL_PLACEHOLDER,
        providers=providers,
    )


def load_settings(
    env: Mapping[str, str] | None = None,
    model_settings_path: str | Path | None = None,
    mcp_services_path: str | Path | None = None,
) -> Settings:
    source = env if env is not None else os.environ
    assert source is not None
    return Settings(
        app_name=_clean_text(source.get("COPY_MYSELF_APP_NAME")) or DEFAULT_APP_NAME,
        log_level=_clean_text(source.get("COPY_MYSELF_LOG_LEVEL")) or DEFAULT_LOG_LEVEL,
        model=_resolve_model_settings(source, model_settings_path),
        mcp_services=load_mcp_service_settings(mcp_services_path),
    )
