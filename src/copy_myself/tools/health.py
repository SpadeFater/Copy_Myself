from __future__ import annotations

from typing import Any

from copy_myself.tools.base import LocalTool, ToolResult


class HealthTool(LocalTool):
    name = "health"
    description = "Reports whether the local agent foundation is reachable."

    def run(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(
            name=self.name,
            ok=True,
            data={"status": "ok", "source": arguments.get("source", "agent")},
        )
