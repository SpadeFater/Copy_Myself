from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from builtin_mcp.tools.base import ToolResult

from .apps import ComOfficeAdapter
from .errors import InvalidOfficeArguments, OfficeUnavailable
from .paths import normalize_roots, resolve_allowed_path


READ_ONLY_ACTIONS = {"list_apps", "word_read_text", "excel_list_sheets", "excel_read_range", "powerpoint_list_slides", "powerpoint_read_text"}
SIDE_EFFECT_ACTIONS = {"open", "close", "save_as", "export_pdf", "create_word", "create_excel", "create_powerpoint", "word_replace_text", "excel_write_range"}
APP_WHITELIST = {"word", "excel", "powerpoint", "wps_word", "wps_excel", "wps_powerpoint"}


class OfficeTool:
    name = "office"
    description = "Safely controls Office or WPS documents inside allowed roots."
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": sorted(READ_ONLY_ACTIONS | SIDE_EFFECT_ACTIONS),
            },
            "app": {"type": "string", "enum": sorted(APP_WHITELIST)},
            "path": {"type": "string"},
            "destination": {"type": "string"},
            "sheet": {"type": "string"},
            "range": {"type": "string"},
            "values": {"type": "array"},
            "text": {"type": "string"},
            "replacement": {"type": "string"},
            "expected_hash": {"type": "string"},
            "visible": {"type": "boolean"},
            "overwrite": {"type": "boolean"},
        },
        "required": ["action"],
        "additionalProperties": False,
    }

    def __init__(self, allowed_roots: list[Path] | None = None, adapter: Any | None = None) -> None:
        self._allowed_roots = normalize_roots(allowed_roots)
        self._adapter = adapter

    def run(self, arguments: dict[str, Any]) -> ToolResult:
        action = str(arguments.get("action", "")).strip()
        if action not in READ_ONLY_ACTIONS | SIDE_EFFECT_ACTIONS:
            return ToolResult(name=self.name, ok=False, error=f"InvalidArguments: unsupported action {action!r}")
        try:
            if action == "list_apps":
                adapter = self._adapter_or_default()
                if not getattr(adapter, "available", True):
                    raise OfficeUnavailable("OfficeUnavailable: install copy-myself[office] on Windows")
                return ToolResult(name=self.name, ok=True, data={"action": action, "apps": adapter.list_apps()})

            app = self._resolve_app(action, arguments.get("app"))
            visible = bool(arguments.get("visible", False))
            path = self._require_path(arguments, action)
            destination = self._require_destination(arguments, action)

            adapter = self._adapter_or_default()
            if not getattr(adapter, "available", True):
                raise OfficeUnavailable("OfficeUnavailable: install copy-myself[office] on Windows")

            if action == "open":
                return ToolResult(name=self.name, ok=True, data=adapter.open(app, path, visible))
            if action == "close":
                return ToolResult(name=self.name, ok=True, data=adapter.close(app, path))
            if action == "create_word":
                return ToolResult(name=self.name, ok=True, data=adapter.create_word(app, destination, visible))
            if action == "create_excel":
                return ToolResult(name=self.name, ok=True, data=adapter.create_excel(app, destination, visible))
            if action == "create_powerpoint":
                return ToolResult(name=self.name, ok=True, data=adapter.create_powerpoint(app, destination, visible))
            if action == "save_as":
                return ToolResult(name=self.name, ok=True, data=adapter.save_as(app, path, destination, visible))
            if action == "export_pdf":
                return ToolResult(name=self.name, ok=True, data=adapter.export_pdf(app, path, destination, visible))
            if action == "word_read_text":
                return ToolResult(name=self.name, ok=True, data=adapter.word_read_text(path, visible))
            if action == "word_replace_text":
                self._require_text(arguments)
                return ToolResult(name=self.name, ok=True, data=adapter.word_replace_text(path, str(arguments.get("text", "")), str(arguments.get("replacement", "")), visible))
            if action == "excel_list_sheets":
                return ToolResult(name=self.name, ok=True, data=adapter.excel_list_sheets(path, visible))
            if action == "excel_read_range":
                self._require_sheet_and_range(arguments)
                return ToolResult(name=self.name, ok=True, data=adapter.excel_read_range(path, str(arguments.get("sheet", "")), str(arguments.get("range", "")), visible))
            if action == "excel_write_range":
                self._require_sheet_and_range(arguments)
                return ToolResult(name=self.name, ok=True, data=adapter.excel_write_range(path, str(arguments.get("sheet", "")), str(arguments.get("range", "")), self._normalize_values(arguments.get("values")), visible))
            if action == "powerpoint_list_slides":
                return ToolResult(name=self.name, ok=True, data=adapter.powerpoint_list_slides(path, visible))
            if action == "powerpoint_read_text":
                return ToolResult(name=self.name, ok=True, data=adapter.powerpoint_read_text(path, visible))
            return ToolResult(name=self.name, ok=False, error=f"NotImplemented: {action}")
        except (InvalidOfficeArguments, OfficeUnavailable, ValueError) as exc:
            return ToolResult(name=self.name, ok=False, error=str(exc))

    def _adapter_or_default(self) -> Any:
        return self._adapter or ComOfficeAdapter()

    def _validate_app(self, raw_app: object) -> str:
        app = str(raw_app or "").strip()
        if app not in APP_WHITELIST:
            raise InvalidOfficeArguments(f"InvalidArguments: unsupported app {app!r}")
        return app

    def _resolve_app(self, action: str, raw_app: object) -> str:
        if raw_app is not None:
            return self._validate_app(raw_app)
        if action in {"create_word", "save_as", "export_pdf", "word_read_text", "word_replace_text", "open", "close"}:
            return "word"
        if action in {"create_excel", "excel_list_sheets", "excel_read_range", "excel_write_range"}:
            return "excel"
        if action in {"create_powerpoint", "powerpoint_list_slides", "powerpoint_read_text"}:
            return "powerpoint"
        raise InvalidOfficeArguments("InvalidArguments: app is required")

    def _resolve_path(self, raw_path: object) -> Path:
        return resolve_allowed_path(raw_path, self._allowed_roots)

    def _require_path(self, arguments: dict[str, Any], action: str) -> Path | None:
        if action in {"list_apps", "create_word", "create_excel", "create_powerpoint"}:
            return None
        if arguments.get("path") is None:
            raise InvalidOfficeArguments("InvalidArguments: path is required")
        return self._resolve_path(arguments.get("path"))

    def _require_destination(self, arguments: dict[str, Any], action: str) -> Path | None:
        if action not in {"save_as", "export_pdf", "create_word", "create_excel", "create_powerpoint"}:
            return None
        if arguments.get("destination") is None:
            raise InvalidOfficeArguments("InvalidArguments: destination is required")
        return self._resolve_destination(arguments.get("destination"), arguments.get("expected_hash"), bool(arguments.get("overwrite", False)))

    def _resolve_destination(self, raw_path: object, expected_hash: object, overwrite: bool) -> Path:
        path = resolve_allowed_path(raw_path, self._allowed_roots)
        if path.exists():
            if not overwrite:
                raise InvalidOfficeArguments(f"AlreadyExists: {path}")
            self._check_expected_hash(path, expected_hash)
        elif not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _check_expected_hash(self, path: Path, expected_hash: object) -> str:
        if not expected_hash:
            raise InvalidOfficeArguments(f"HashRequired: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if str(expected_hash) != digest:
            raise InvalidOfficeArguments(f"HashMismatch: {path}")
        return digest

    def _normalize_values(self, values: object) -> list[list[Any]]:
        if values is None:
            return []
        if not isinstance(values, list):
            raise InvalidOfficeArguments("InvalidArguments: values must be a list")
        return [row if isinstance(row, list) else [row] for row in values]

    def _require_text(self, arguments: dict[str, Any]) -> None:
        if arguments.get("text") is None:
            raise InvalidOfficeArguments("InvalidArguments: text is required")
        if arguments.get("replacement") is None:
            raise InvalidOfficeArguments("InvalidArguments: replacement is required")

    def _require_sheet_and_range(self, arguments: dict[str, Any]) -> None:
        if not str(arguments.get("sheet", "")).strip():
            raise InvalidOfficeArguments("InvalidArguments: sheet is required")
        if not str(arguments.get("range", "")).strip():
            raise InvalidOfficeArguments("InvalidArguments: range is required")
