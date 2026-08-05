from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolPolicy:
    def requires_approval(self, origin: str, metadata: dict[str, Any]) -> bool:
        if origin != "builtin":
            return True
        project_meta = metadata.get("_meta", {}).get("copy_myself", {}) or metadata.get("copy_myself", {})
        risk = project_meta.get("risk")
        if risk is not None:
            return risk != "read_only"
        annotations = metadata.get("annotations", {})
        return annotations.get("readOnlyHint") is not True
