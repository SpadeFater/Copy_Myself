from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .naming import canonical_tool_name, model_tool_name


@dataclass(frozen=True)
class ToolDescriptor:
    service_id: str
    downstream_name: str
    canonical_name: str
    model_name: str
    description: str
    input_schema: dict[str, Any]
    annotations: dict[str, Any] = field(default_factory=dict)
    origin: str = "external"
    connection_status: str = "online"


class ToolCatalog:
    def __init__(self) -> None:
        self._items: dict[str, ToolDescriptor] = {}

    def add(self, descriptor: ToolDescriptor) -> None:
        if descriptor.model_name in self._items:
            raise ValueError("tool_name_collision")
        self._items[descriptor.model_name] = descriptor

    def replace_service(self, service_id: str, descriptors: list[ToolDescriptor]) -> None:
        for key in [key for key, item in self._items.items() if item.service_id == service_id]:
            del self._items[key]
        for item in descriptors:
            self.add(item)

    def get_by_model_name(self, name: str) -> ToolDescriptor | None:
        return self._items.get(name)

    def definitions(self) -> list[dict[str, Any]]:
        return [{"type": "function", "function": {"name": i.model_name, "description": i.description, "parameters": i.input_schema}} for i in self._items.values()]

    def items(self) -> list[ToolDescriptor]:
        return list(self._items.values())


def descriptor(service_id: str, tool: Any, *, origin: str) -> ToolDescriptor:
    name = getattr(tool, "name", "")
    canonical = canonical_tool_name(service_id, name)
    annotations = dict(getattr(tool, "meta", None) or {})
    if getattr(tool, "annotations", None):
        annotations["annotations"] = tool.annotations.model_dump(exclude_none=True)
    return ToolDescriptor(service_id, name, canonical, model_tool_name(service_id, name), getattr(tool, "description", ""), getattr(tool, "inputSchema", getattr(tool, "parameters", {})), annotations, origin)
