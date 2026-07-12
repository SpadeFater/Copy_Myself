import copy_myself.config as config
from copy_myself.config import (
    McpServiceSettings,
    ModelSettings,
    list_mcp_service_settings,
    list_model_settings,
    load_settings,
    save_mcp_service_settings,
    save_model_settings,
    switch_active_model,
)


def test_load_settings_reads_local_env_file(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "COPY_MYSELF_MODEL_NAME=test-model",
                "COPY_MYSELF_API_KEY=test-key",
                "COPY_MYSELF_BASE_URL=https://example.test/v1",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    settings = load_settings()

    assert settings.model_name == "test-model"
    assert settings.api_key == "test-key"
    assert settings.base_url == "https://example.test/v1"


def test_load_settings_reads_project_env_file_when_cwd_differs(tmp_path, monkeypatch) -> None:
    project_root = tmp_path / "project"
    package_dir = project_root / "src" / "copy_myself"
    package_dir.mkdir(parents=True)
    (project_root / ".env").write_text(
        "\n".join(
            [
                "COPY_MYSELF_MODEL_NAME=project-model",
                "COPY_MYSELF_API_KEY=project-key",
            ]
        ),
        encoding="utf-8",
    )
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir(exist_ok=True)
    monkeypatch.chdir(outside_dir)
    monkeypatch.setattr(config, "__file__", str(package_dir / "config.py"))

    settings = load_settings()

    assert settings.model_name == "project-model"
    assert settings.api_key == "project-key"


def test_save_model_settings_updates_env_file_and_runtime_env(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("COPY_MYSELF_ACTIVE_MODEL", raising=False)
    monkeypatch.delenv("COPY_MYSELF_MODEL_NAME", raising=False)
    monkeypatch.delenv("COPY_MYSELF_API_KEY", raising=False)
    monkeypatch.delenv("COPY_MYSELF_BASE_URL", raising=False)
    monkeypatch.delenv("COPY_MYSELF_MODEL_PROFILES", raising=False)

    save_model_settings(
        ModelSettings(
            model_name="openrouter/auto",
            api_key="secret-key",
            base_url="https://openrouter.ai/api/v1",
        ),
        env_path=tmp_path / ".env",
    )

    env_content = (tmp_path / ".env").read_text(encoding="utf-8")
    settings = load_settings()
    profiles = list_model_settings(env_path=tmp_path / ".env")

    assert "COPY_MYSELF_ACTIVE_MODEL=openrouter/auto" in env_content
    assert "COPY_MYSELF_MODEL_NAME=openrouter/auto" in env_content
    assert "COPY_MYSELF_API_KEY=secret-key" in env_content
    assert "COPY_MYSELF_BASE_URL=https://openrouter.ai/api/v1" in env_content
    assert settings.model_name == "openrouter/auto"
    assert settings.api_key == "secret-key"
    assert settings.base_url == "https://openrouter.ai/api/v1"
    assert profiles == [
        ModelSettings(
            model_name="openrouter/auto",
            api_key="secret-key",
            base_url="https://openrouter.ai/api/v1",
        )
    ]


def test_switch_active_model_loads_saved_profile(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("COPY_MYSELF_ACTIVE_MODEL", raising=False)
    monkeypatch.delenv("COPY_MYSELF_MODEL_NAME", raising=False)
    monkeypatch.delenv("COPY_MYSELF_API_KEY", raising=False)
    monkeypatch.delenv("COPY_MYSELF_BASE_URL", raising=False)
    monkeypatch.delenv("COPY_MYSELF_MODEL_PROFILES", raising=False)
    env_path = tmp_path / ".env"
    save_model_settings(
        ModelSettings("model-a", "key-a", "https://a.test/v1"),
        env_path=env_path,
    )
    save_model_settings(
        ModelSettings("model-b", "key-b", "https://b.test/v1"),
        env_path=env_path,
    )

    switch_active_model("model-a", env_path=env_path)

    settings = load_settings()
    assert settings.model_name == "model-a"
    assert settings.api_key == "key-a"
    assert settings.base_url == "https://a.test/v1"


def test_active_model_profile_takes_priority_over_legacy_model_fields(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    env_path = tmp_path / ".env"
    save_model_settings(
        ModelSettings("model-a", "key-a", "https://a.test/v1"),
        env_path=env_path,
    )
    save_model_settings(
        ModelSettings("model-b", "key-b", "https://b.test/v1"),
        env_path=env_path,
    )
    monkeypatch.setenv("COPY_MYSELF_ACTIVE_MODEL", "model-a")
    monkeypatch.setenv("COPY_MYSELF_MODEL_NAME", "model-b")
    monkeypatch.setenv("COPY_MYSELF_API_KEY", "key-b")
    monkeypatch.setenv("COPY_MYSELF_BASE_URL", "https://b.test/v1")

    settings = load_settings()

    assert settings.model_name == "model-a"
    assert settings.api_key == "key-a"
    assert settings.base_url == "https://a.test/v1"


def test_save_mcp_service_settings_updates_env_file(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("COPY_MYSELF_MCP_SERVICES", raising=False)
    env_path = tmp_path / ".env"

    save_mcp_service_settings(
        McpServiceSettings(name="filesystem", endpoint="npx -y @modelcontextprotocol/server-filesystem ."),
        env_path=env_path,
    )

    services = list_mcp_service_settings(env_path=env_path)
    env_content = env_path.read_text(encoding="utf-8")

    assert services == [
        McpServiceSettings(name="filesystem", endpoint="npx -y @modelcontextprotocol/server-filesystem .")
    ]
    assert "COPY_MYSELF_MCP_SERVICES=" in env_content
