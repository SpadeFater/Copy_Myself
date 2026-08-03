from pathlib import Path

from agent.graph import create_default_registry, default_filesystem_roots
from tools import TimeTool, ToolRegistry


def test_registry_runs_registered_tool() -> None:
    registry = ToolRegistry()
    registry.register(TimeTool())

    result = registry.run("getTime", {"source": "test", "timezone": "UTC"})

    assert result.name == "getTime"
    assert result.ok is True
    assert result.data["status"] == "ok"
    assert result.data["timezone"] == "UTC"


def test_registry_reports_missing_tool() -> None:
    registry = ToolRegistry()

    result = registry.run("missing", {})

    assert result.name == "missing"
    assert result.ok is False
    assert "not registered" in result.error


def test_default_registry_includes_filesystem_tool() -> None:
    registry = create_default_registry()

    assert "filesystem" in registry.names()


def test_default_registry_exposes_filesystem_as_read_write_tool() -> None:
    registry = create_default_registry()

    definitions = registry.definitions()
    filesystem = next(item for item in definitions if item["function"]["name"] == "filesystem")

    assert "reads and writes" in filesystem["function"]["description"]
    assert "write" in filesystem["function"]["parameters"]["properties"]["action"]["enum"]


def test_default_filesystem_roots_include_user_file_locations(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    roots = default_filesystem_roots()

    assert tmp_path / "Desktop" in roots
    assert tmp_path / "Documents" in roots
    assert tmp_path / "Downloads" in roots
