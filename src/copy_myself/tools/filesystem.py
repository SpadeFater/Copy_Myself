from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from copy_myself.tools.base import ToolResult


SKIP_DIRS = {".git", ".pytest_cache", "__pycache__", ".venv", "venv", "node_modules", "dist", "build"}
SENSITIVE_NAMES = {".env", "keys", "id_rsa", "id_ed25519"}


class FileSystemTool:
    name = "filesystem"
    description = "Read-only access to files within allowed roots."
    _max_read_bytes = 64 * 1024

    def __init__(self, allowed_roots: list[Path] | None = None) -> None:
        roots = allowed_roots or [Path.cwd()]
        self._allowed_roots = [Path(root).resolve() for root in roots]

    def run(self, arguments: dict[str, Any]) -> ToolResult:
        action = arguments.get("action")
        if action not in {"list", "stat", "read", "search", "write", "mkdir"}:
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
            if action == "search":
                return self._search(path, arguments)
            if action == "write":
                return self._write(path, arguments)
            if action == "mkdir":
                return self._mkdir(path, arguments)
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

    def _relative(self, path: Path) -> str:
        for root in self._allowed_roots:
            try:
                return path.relative_to(root).as_posix()
            except ValueError:
                continue
        raise ValueError(f"PathOutsideRoot: {path}")

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

    def _is_sensitive(self, path: Path) -> bool:
        if ".git" in path.parts:
            return True
        return path.name in SENSITIVE_NAMES or path.name.startswith(".env.")

    def _ensure_not_sensitive(self, path: Path) -> None:
        if self._is_sensitive(path):
            raise ValueError(f"SensitivePath: {self._relative(path)}")

    def _check_expected_hash(self, path: Path, expected_hash: Any) -> str:
        current_hash = self._sha256(path)
        if not expected_hash:
            raise ValueError(f"HashRequired: {self._relative(path)}")
        if str(expected_hash) != current_hash:
            raise ValueError(f"HashMismatch: {self._relative(path)}")
        return current_hash

    def _entry(self, path: Path) -> dict[str, Any]:
        stat = path.stat()
        return {
            "name": path.name,
            "path": self._relative(path),
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
        data = self._entry(path)
        data["absolute_path"] = str(path)
        if path.is_file():
            data["sha256"] = self._sha256(path)
        return ToolResult(name=self.name, ok=True, data=data)

    def _read(self, path: Path, arguments: dict[str, Any]) -> ToolResult:
        if not path.is_file():
            raise ValueError(f"InvalidArguments: not a file {path}")
        if self._is_binary(path):
            raise ValueError(f"BinaryFile: {self._relative(path)}")

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
            data={
                "action": "read",
                "content": content,
                "sha256": self._sha256(path),
                "truncated": truncated,
            },
        )

    def _walk_files(self, root: Path) -> list[Path]:
        files: list[Path] = []
        for current, dirs, names in os.walk(root):
            dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
            for name in names:
                files.append(Path(current) / name)
        return files

    def _search(self, root: Path, arguments: dict[str, Any]) -> ToolResult:
        query = str(arguments.get("query", ""))
        if not query:
            raise ValueError("InvalidArguments: query is required")

        mode = str(arguments.get("mode", "content"))
        limit = int(arguments.get("limit", 50))
        files = [root] if root.is_file() else self._walk_files(root)
        matches: list[dict[str, Any]] = []

        for path in files:
            if len(matches) >= limit:
                break
            if mode == "name":
                if query.casefold() in path.name.casefold():
                    matches.append({"path": self._relative(path), "kind": "file"})
                continue
            if mode == "content":
                if self._is_binary(path):
                    continue
                try:
                    content = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                if query in content:
                    matches.append({"path": self._relative(path), "kind": "file"})
                continue
            raise ValueError(f"InvalidArguments: unsupported search mode {mode!r}")

        return ToolResult(
            name=self.name,
            ok=True,
            data={"action": "search", "query": query, "mode": mode, "matches": matches},
        )

    def _mkdir(self, path: Path, arguments: dict[str, Any]) -> ToolResult:
        self._ensure_not_sensitive(path)
        path.mkdir(parents=bool(arguments.get("parents", False)), exist_ok=bool(arguments.get("exist_ok", True)))
        return ToolResult(name=self.name, ok=True, data={"action": "mkdir", "path": self._relative(path)})

    def _write(self, path: Path, arguments: dict[str, Any]) -> ToolResult:
        self._ensure_not_sensitive(path)
        content = str(arguments.get("content", ""))
        if not path.parent.exists():
            if not bool(arguments.get("create_parents", False)):
                raise ValueError(f"InvalidArguments: parent does not exist {self._relative(path.parent)}")
            path.parent.mkdir(parents=True, exist_ok=True)

        before_hash = None
        if path.exists():
            if not path.is_file():
                raise ValueError(f"InvalidArguments: not a file {self._relative(path)}")
            before_hash = self._check_expected_hash(path, arguments.get("expected_hash"))

        path.write_text(content, encoding="utf-8")
        return ToolResult(
            name=self.name,
            ok=True,
            data={
                "action": "write",
                "path": self._relative(path),
                "before_sha256": before_hash,
                "after_sha256": self._sha256(path),
                "changed": [self._relative(path)],
            },
        )
