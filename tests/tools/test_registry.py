from __future__ import annotations

from dataclasses import dataclass

from copy_myself.tools import HealthTool, ToolRegistry, ToolResult
from copy_myself.tools.registry import ToolSource


@dataclass
class CustomTool:
    name: str = "custom"
    description: str = "Custom test tool."

    def run(self, arguments):
        return ToolResult(name=self.name, ok=True, data={"value": arguments.get("value")})


class CustomSource(ToolSource):
    def list_tools(self):
        return [CustomTool()]

    def invoke(self, name, arguments):
        assert name == "custom"
        tool = CustomTool()
        return tool.run(arguments)


def test_registry_auto_discovers_local_tool_subclasses() -> None:
    registry = ToolRegistry(discover=True)

    assert "health" in registry.names()

    result = registry.run("health", {"source": "test"})
    assert result.ok is True
    assert result.data["status"] == "ok"


def test_registry_can_register_external_tool_source() -> None:
    registry = ToolRegistry(discover=False)
    registry.load_source(CustomSource())

    result = registry.run("custom", {"value": 42})

    assert result.ok is True
    assert result.data == {"value": 42}


def test_registry_reports_source_tools_in_names() -> None:
    registry = ToolRegistry(discover=False)
    registry.load_source(CustomSource())

    assert registry.names() == ["custom"]
