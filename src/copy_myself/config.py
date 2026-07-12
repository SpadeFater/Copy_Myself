from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "Copy_Myself"
    log_level: str = "INFO"
    model_name: str = "deepseek-v4-pro"
    api_key: str = ""
    base_url: str = "https://api.deepseek.com/v1"


@dataclass(frozen=True)
class ModelSettings:
    model_name: str
    api_key: str
    base_url: str


@dataclass(frozen=True)
class McpServiceSettings:
    name: str
    endpoint: str


@dataclass(frozen=True)
class ProviderSettings:
    provider: str
    model_name: str
    api_key: str
    base_url: str


def load_settings() -> Settings:
    env_file = _read_env_file(_find_env_file())
    active_model = _get_setting("COPY_MYSELF_ACTIVE_MODEL", env_file, "")
    profile = _find_model_profile(active_model, env_file) if active_model else None

    if profile is not None:
        return Settings(
            app_name=_get_setting("COPY_MYSELF_APP_NAME", env_file, "Copy_Myself"),
            log_level=_get_setting("COPY_MYSELF_LOG_LEVEL", env_file, "INFO"),
            model_name=profile.model_name,
            api_key=profile.api_key,
            base_url=profile.base_url,
        )
    else:
        default_model = "deepseek-v4-pro"
        default_api_key = ""
        default_base_url = "https://api.deepseek.com/v1"

    return Settings(
        app_name=_get_setting("COPY_MYSELF_APP_NAME", env_file, "Copy_Myself"),
        log_level=_get_setting("COPY_MYSELF_LOG_LEVEL", env_file, "INFO"),
        model_name=_get_setting("COPY_MYSELF_MODEL_NAME", env_file, default_model),
        api_key=_get_setting("COPY_MYSELF_API_KEY", env_file, default_api_key),
        base_url=_get_setting("COPY_MYSELF_BASE_URL", env_file, default_base_url),
    )


def list_model_settings(env_path: Path | None = None) -> list[ModelSettings]:
    values = _read_env_file(env_path or _find_env_file())
    return _read_model_profiles(values)


def list_mcp_service_settings(env_path: Path | None = None) -> list[McpServiceSettings]:
    values = _read_env_file(env_path or _find_env_file())
    return _read_mcp_services(values)


def save_model_settings(settings: ModelSettings, env_path: Path | None = None) -> None:
    path = env_path or _find_env_file()
    values = _read_env_file(path)
    profiles = [
        profile
        for profile in _read_model_profiles(values)
        if profile.model_name != settings.model_name
    ]
    profiles.append(settings)
    updates = {
        "COPY_MYSELF_ACTIVE_MODEL": settings.model_name,
        "COPY_MYSELF_MODEL_NAME": settings.model_name,
        "COPY_MYSELF_API_KEY": settings.api_key,
        "COPY_MYSELF_BASE_URL": settings.base_url,
        "COPY_MYSELF_MODEL_PROFILES": _encode_model_profiles(profiles),
    }
    values.update(updates)
    _write_env_file(path, values)
    for name, value in updates.items():
        os.environ[name] = value


def switch_active_model(model_name: str, env_path: Path | None = None) -> ModelSettings:
    path = env_path or _find_env_file()
    values = _read_env_file(path)
    profile = _find_model_profile(model_name, values)
    if profile is None:
        raise ValueError(f"Model profile '{model_name}' is not saved.")

    updates = {
        "COPY_MYSELF_ACTIVE_MODEL": profile.model_name,
        "COPY_MYSELF_MODEL_NAME": profile.model_name,
        "COPY_MYSELF_API_KEY": profile.api_key,
        "COPY_MYSELF_BASE_URL": profile.base_url,
    }
    values.update(updates)
    _write_env_file(path, values)
    for name, value in updates.items():
        os.environ[name] = value
    return profile


def save_mcp_service_settings(settings: McpServiceSettings, env_path: Path | None = None) -> None:
    clean_name = settings.name.strip()
    clean_endpoint = settings.endpoint.strip()
    if not clean_name:
        raise ValueError("MCP service name is required.")
    if not clean_endpoint:
        raise ValueError("MCP service command or URL is required.")

    path = env_path or _find_env_file()
    values = _read_env_file(path)
    services = [
        service
        for service in _read_mcp_services(values)
        if service.name != clean_name
    ]
    services.append(McpServiceSettings(name=clean_name, endpoint=clean_endpoint))
    encoded = _encode_mcp_services(services)
    values["COPY_MYSELF_MCP_SERVICES"] = encoded
    _write_env_file(path, values)
    os.environ["COPY_MYSELF_MCP_SERVICES"] = encoded


def save_provider_settings(settings: ProviderSettings, env_path: Path | None = None) -> None:
    save_model_settings(
        ModelSettings(
            model_name=settings.model_name,
            api_key=settings.api_key,
            base_url=settings.base_url,
        ),
        env_path=env_path,
    )


def _get_setting(name: str, env_file: dict[str, str], default: str) -> str:
    return os.getenv(name) or env_file.get(name) or default


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip().strip('"').strip("'")
    return values


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{name}={value}" for name, value in values.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_model_profiles(values: dict[str, str]) -> list[ModelSettings]:
    raw_profiles = values.get("COPY_MYSELF_MODEL_PROFILES", "")
    profiles: list[ModelSettings] = []
    if raw_profiles:
        try:
            decoded = json.loads(raw_profiles)
        except json.JSONDecodeError:
            decoded = []
        for item in decoded:
            if not isinstance(item, dict):
                continue
            model_name = str(item.get("model_name", "")).strip()
            base_url = str(item.get("base_url", "")).strip()
            api_key = str(item.get("api_key", "")).strip()
            if model_name and base_url:
                profiles.append(ModelSettings(model_name=model_name, api_key=api_key, base_url=base_url))

    legacy_model = values.get("COPY_MYSELF_MODEL_NAME", "").strip()
    legacy_base_url = values.get("COPY_MYSELF_BASE_URL", "").strip()
    legacy_api_key = values.get("COPY_MYSELF_API_KEY", "").strip()
    if legacy_model and legacy_base_url and all(profile.model_name != legacy_model for profile in profiles):
        profiles.append(ModelSettings(legacy_model, legacy_api_key, legacy_base_url))
    return profiles


def _read_mcp_services(values: dict[str, str]) -> list[McpServiceSettings]:
    raw_services = values.get("COPY_MYSELF_MCP_SERVICES", "")
    services: list[McpServiceSettings] = []
    if not raw_services:
        return services

    try:
        decoded = json.loads(raw_services)
    except json.JSONDecodeError:
        return services

    for item in decoded:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        endpoint = str(item.get("endpoint", "")).strip()
        if name and endpoint:
            services.append(McpServiceSettings(name=name, endpoint=endpoint))
    return services


def _encode_model_profiles(profiles: list[ModelSettings]) -> str:
    return json.dumps(
        [
            {
                "model_name": profile.model_name,
                "base_url": profile.base_url,
                "api_key": profile.api_key,
            }
            for profile in profiles
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _encode_mcp_services(services: list[McpServiceSettings]) -> str:
    return json.dumps(
        [
            {
                "name": service.name,
                "endpoint": service.endpoint,
            }
            for service in services
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _find_model_profile(model_name: str, values: dict[str, str]) -> ModelSettings | None:
    for profile in _read_model_profiles(values):
        if profile.model_name == model_name:
            return profile
    return None


def _find_env_file() -> Path:
    cwd_env = Path(".env")
    if cwd_env.exists():
        return cwd_env

    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.exists():
            return candidate
    return cwd_env
