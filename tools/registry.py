from __future__ import annotations

from typing import Any

from tools.base import Tool, ToolResult


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def run(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(name=name, ok=False, error=f"Tool '{name}' is not registered.")
        try:
            return tool.run(arguments)
        except Exception as exc:
            return ToolResult(name=name, ok=False, error=str(exc))

    def names(self) -> list[str]:
        return sorted(self._tools)

    def definitions(self) -> list[dict[str, Any]]:
        definitions: list[dict[str, Any]] = []
        for tool in self._tools.values():
            definitions.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": getattr(
                            tool,
                            "parameters",
                            {"type": "object", "properties": {}, "additionalProperties": True},
                        ),
                    },
                }
            )
        return definitions
