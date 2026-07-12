from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from copy_myself.tools.base import Tool, ToolResult
from copy_myself.tools.mcp import LocalToolSource, ToolCatalogItem, ToolSource


@dataclass
class ToolRegistry:
    discover: bool = True
    _sources: dict[str, ToolSource] = field(default_factory=dict, init=False)
    _catalog: dict[str, ToolCatalogItem] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.discover:
            self.load_source(LocalToolSource.discover())

    def register(self, tool: Tool) -> None:
        self.load_source(LocalToolSource({tool.name: tool}))

    def load_source(self, source: ToolSource) -> None:
        for item in source.list_tools():
            self._sources[item.name] = source
            self._catalog[item.name] = item

    def run(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        source = self._sources.get(name)
        if source is None:
            return ToolResult(name=name, ok=False, error=f"Tool '{name}' is not registered.")
        try:
            return source.invoke(name, arguments)
        except Exception as exc:
            return ToolResult(name=name, ok=False, error=str(exc))

    def names(self) -> list[str]:
        return sorted(self._sources)

    def catalog(self) -> list[ToolCatalogItem]:
        return [self._catalog[name] for name in self.names()]
