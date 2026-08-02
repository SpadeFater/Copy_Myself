from copy_myself.tools import HealthTool, ToolRegistry
from copy_myself.agent.graph import create_default_registry


def test_registry_runs_registered_tool() -> None:
    registry = ToolRegistry()
    registry.register(HealthTool())

    result = registry.run("health", {"source": "test"})

    assert result.name == "health"
    assert result.ok is True
    assert result.data["status"] == "ok"


def test_registry_reports_missing_tool() -> None:
    registry = ToolRegistry()

    result = registry.run("missing", {})

    assert result.name == "missing"
    assert result.ok is False
    assert "not registered" in result.error


def test_default_registry_includes_filesystem_tool() -> None:
    registry = create_default_registry()

    assert "filesystem" in registry.names()
