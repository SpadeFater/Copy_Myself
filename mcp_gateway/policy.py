from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolPolicy:
    def requires_approval(self, origin: str, metadata: dict[str, Any]) -> bool:
        if origin not in {"builtin", "generated"}:
            return True
        project_meta = metadata.get("_meta", {}).get("copy_myself", {}) or metadata.get("copy_myself", {})
        risk = project_meta.get("risk")
        if risk is not None:
            return risk != "read_only"
        annotations = metadata.get("annotations", {})
        if origin == "generated":
            return project_meta.get("risk") != "read_only"
        return annotations.get("readOnlyHint") is not True
