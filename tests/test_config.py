from __future__ import annotations

from config import (
    McpServiceSettings,
    ModelProviderSettings,
    import_mcp_service_setting,
    import_model_provider_setting,
    list_mcp_service_settings,
    list_model_provider_settings,
    load_settings,
    save_mcp_service_settings,
    save_model_provider_settings,
)


def test_load_settings_prefers_active_model(monkeypatch) -> None:
    monkeypatch.setenv("COPY_MYSELF_ACTIVE_MODEL", "gpt-5.6-sol")
    monkeypatch.setenv("COPY_MYSELF_MODEL_NAME", "legacy-model")

    settings = load_settings()

    assert settings.model.current_model == "gpt-5.6-sol"
    assert settings.model.source == "COPY_MYSELF_ACTIVE_MODEL"


def test_load_settings_uses_legacy_model_when_active_missing(monkeypatch) -> None:
    monkeypatch.delenv("COPY_MYSELF_ACTIVE_MODEL", raising=False)
    monkeypatch.setenv("COPY_MYSELF_MODEL_NAME", "legacy-model")

    settings = load_settings()

    assert settings.model.current_model == "legacy-model"
    assert settings.model.source == "COPY_MYSELF_MODEL_NAME"


def test_mcp_service_settings_round_trip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COPY_MYSELF_CONFIG_DIR", str(tmp_path))

    saved = save_mcp_service_settings(
        [
            McpServiceSettings(
                name="Local Desktop",
                endpoint="http://127.0.0.1:3000",
                transport="http",
                command="",
                args=("alpha", "beta"),
            )
        ]
    )

    assert saved[0].name == "Local Desktop"
    assert list_mcp_service_settings() == saved


def test_model_provider_settings_round_trip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COPY_MYSELF_CONFIG_DIR", str(tmp_path))

    saved = save_model_provider_settings(
        [
            ModelProviderSettings(
                name="Local Qwen",
                base_url="http://127.0.0.1:11434/v1",
                model_name="qwen2.5:7b",
                api_key="local-key",
            )
        ]
    )

    assert saved[0].name == "Local Qwen"
    assert saved[0].base_url == "http://127.0.0.1:11434/v1"
    assert list_model_provider_settings() == saved


def test_imported_model_can_be_current_model(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COPY_MYSELF_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("COPY_MYSELF_ACTIVE_MODEL", raising=False)
    monkeypatch.delenv("COPY_MYSELF_CURRENT_MODEL", raising=False)
    monkeypatch.delenv("COPY_MYSELF_MODEL", raising=False)
    monkeypatch.delenv("COPY_MYSELF_MODEL_NAME", raising=False)

    provider = import_model_provider_setting(
        name="Remote Gateway",
        base_url="https://models.example.com/v1",
        model_name="copy-agent-large",
    )

    settings = load_settings()

    assert settings.model_name == "copy-agent-large"
    assert settings.model.source == "imported-model"
    assert settings.model.providers == (provider,)


def test_import_mcp_service_setting_persists_service(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COPY_MYSELF_CONFIG_DIR", str(tmp_path))

    service = import_mcp_service_setting(
        "https://mcp.example.com",
        name="Example MCP",
        transport="http",
        command="npx",
        args=("--yes", "mcp-server"),
    )

    assert service.name == "Example MCP"
    assert service.endpoint == "https://mcp.example.com"
    assert service.transport == "http"
    assert service.command == "npx"
    assert service.args == ("--yes", "mcp-server")
    assert list_mcp_service_settings() == (service,)
