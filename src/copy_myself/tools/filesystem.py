from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from copy_myself.tools.base import ToolResult


class FileSystemTool:
    name = "filesystem"
    description = "Read-only access to files within allowed roots."
    _max_read_bytes = 64 * 1024

    def __init__(self, allowed_roots: list[Path] | None = None) -> None:
        roots = allowed_roots or [Path.cwd()]
        self._allowed_roots = [Path(root).resolve() for root in roots]

    def run(self, arguments: dict[str, Any]) -> ToolResult:
        action = arguments.get("action")
        if action not in {"list", "stat", "read"}:
            return ToolResult(
                name=self.name,
                ok=False,
                error=f"InvalidArguments: unsupported action {action!r}",
            )

        try:
            path = self._resolve(arguments.get("path", "."))
            if action == "list":
                return self._list(path)
            if action == "stat":
                return self._stat(path)
            return self._read(path, arguments)
        except OSError as exc:
            return ToolResult(name=self.name, ok=False, error=f"FileSystemError: {exc}")
        except ValueError as exc:
            return ToolResult(name=self.name, ok=False, error=str(exc))

    def _resolve(self, raw_path: object) -> Path:
        path = Path(raw_path) if raw_path is not None else Path(".")
        if not path.is_absolute():
            path = self._allowed_roots[0] / path
        resolved = path.resolve()

        if not any(resolved == root or root in resolved.parents for root in self._allowed_roots):
            raise ValueError(f"PathOutsideRoot: {resolved}")
        return resolved

    def _sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _is_binary(self, path: Path) -> bool:
        with path.open("rb") as file:
            sample = file.read(1024)
        return b"\x00" in sample

    def _entry(self, path: Path) -> dict[str, Any]:
        stat = path.stat()
        return {
            "name": path.name,
            "kind": "directory" if path.is_dir() else "file",
            "size": stat.st_size,
            "modified": stat.st_mtime,
        }

    def _list(self, path: Path) -> ToolResult:
        if not path.is_dir():
            raise ValueError(f"InvalidArguments: not a directory {path}")
        entries = [self._entry(child) for child in sorted(path.iterdir(), key=lambda item: item.name)]
        return ToolResult(name=self.name, ok=True, data={"action": "list", "entries": entries})

    def _stat(self, path: Path) -> ToolResult:
        stat = path.stat()
        data: dict[str, Any] = {
            "kind": "directory" if path.is_dir() else "file",
            "size": stat.st_size,
            "modified": stat.st_mtime,
        }
        if path.is_file():
            data["sha256"] = self._sha256(path)
        return ToolResult(name=self.name, ok=True, data=data)

    def _read(self, path: Path, arguments: dict[str, Any]) -> ToolResult:
        if not path.is_file():
            raise ValueError(f"InvalidArguments: not a file {path}")
        if self._is_binary(path):
            raise ValueError(f"InvalidArguments: binary file {path}")

        offset = int(arguments.get("offset", 0))
        limit = min(int(arguments.get("limit", self._max_read_bytes)), self._max_read_bytes)
        if offset < 0 or limit < 0:
            raise ValueError("InvalidArguments: offset and limit must be non-negative")

        file_size = path.stat().st_size
        with path.open("rb") as file:
            file.seek(offset)
            content_bytes = file.read(limit)
        content = content_bytes.decode("utf-8")
        truncated = offset + len(content_bytes) < file_size

        return ToolResult(
            name=self.name,
            ok=True,
            data={"action": "read", "content": content, "truncated": truncated},
        )
