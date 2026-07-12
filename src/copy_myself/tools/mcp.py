from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from inspect import getmembers, isclass
from pkgutil import iter_modules
from typing import Any, Protocol

from copy_myself.tools.base import LocalTool, Tool, ToolResult


@dataclass(frozen=True)
class ToolCatalogItem:
    name: str
    description: str


class ToolSource(Protocol):
    def list_tools(self) -> list[ToolCatalogItem]:
        """Return the catalog exposed by one MCP-style service."""

    def invoke(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool by name through the source."""


class ToolCatalogSource(Protocol):
    def list_tools(self) -> list[ToolCatalogItem]:
        ...


class LocalToolSource:
    """In-process MCP-style source for locally authored tools."""

    def __init__(self, tools: dict[str, Tool]) -> None:
        self._tools = tools

    @classmethod
    def discover(cls, package_name: str = "copy_myself.tools") -> "LocalToolSource":
        package = import_module(package_name)
        tools: dict[str, Tool] = {}
        for module_info in iter_modules(package.__path__):
            if module_info.name in {"base", "mcp", "registry", "__init__"}:
                continue
            module = import_module(f"{package.__name__}.{module_info.name}")
            for _, candidate in getmembers(module, isclass):
                if candidate is LocalTool or not issubclass(candidate, LocalTool):
                    continue
                if candidate.__module__ != module.__name__:
                    continue
                try:
                    tool = candidate()
                except TypeError:
                    continue
                tools[tool.name] = tool
        return cls(tools)

    def list_tools(self) -> list[ToolCatalogItem]:
        return [
            ToolCatalogItem(name=tool.name, description=tool.description)
            for tool in self._tools.values()
        ]

    def invoke(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(name=name, ok=False, error=f"Tool '{name}' is not registered.")
        try:
            result = tool.run(arguments)
        except Exception as exc:
            return ToolResult(name=name, ok=False, error=str(exc))
        return result if isinstance(result, ToolResult) else ToolResult(name=name, ok=True, data=dict(result))


class McpToolSource:
    """Adapter around an external MCP service client."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def list_tools(self) -> list[ToolCatalogItem]:
        return self._client.list_tools()

    def invoke(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        return self._client.invoke(name, arguments)
