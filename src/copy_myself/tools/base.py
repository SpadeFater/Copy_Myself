from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolResult:
    name: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class Tool(Protocol):
    name: str
    description: str

    def run(self, arguments: dict[str, Any]) -> ToolResult:
        """Run the tool with structured arguments."""


class LocalTool(ABC):
    """Optional base class for locally authored tools.

    Subclassing this class is not required, but it makes local tool discovery
    explicit and keeps tool modules easy to author.
    """

    name: str
    description: str
