from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from builtin_mcp.tools.filesystem import FileSystemTool
from builtin_mcp.tools.office import OfficeTool
from builtin_mcp.tools.time import TimeTool
from builtin_mcp.tools.generated.manager import GeneratedToolManager


def _roots() -> list[Path]:
    configured = os.getenv("COPY_MYSELF_FILESYSTEM_ROOTS", "")
    return [Path(item).expanduser() for item in configured.split(os.pathsep) if item.strip()] or [Path.cwd()]


server = FastMCP("CopyMyself Builtin MCP")


@server.tool(name="getTime", annotations=ToolAnnotations(readOnlyHint=True), meta={"copy_myself": {"risk": "read_only"}})
def get_time(timezone: str | None = None, location: str | None = None) -> dict[str, Any]:
    """Return current time for an IANA timezone or supported location."""
    result = TimeTool().run({"timezone": timezone, "location": location, "source": "mcp"})
    if not result.ok:
        raise ValueError(result.error)
    return result.data


@server.tool(name="filesystem", meta={"copy_myself": {"risk_by_argument": {"action": {"list": "read_only", "stat": "read_only", "read": "read_only", "search": "read_only"}}, "default_risk": "side_effect"}})
def filesystem(
    action: str,
    path: str = ".",
    source: str | None = None,
    destination: str | None = None,
    content: str | None = None,
    query: str | None = None,
    mode: str | None = None,
    patch: str | None = None,
    expected_hash: str | None = None,
    create_parents: bool = False,
    parents: bool = False,
    exist_ok: bool = False,
    overwrite: bool = False,
    recursive: bool = False,
    dry_run: bool = True,
    confirm: bool = False,
    offset: int = 0,
    limit: int | None = None,
) -> dict[str, Any]:
    """Safely read or mutate files inside configured roots."""
    arguments = {key: value for key, value in locals().items() if value is not None}
    result = FileSystemTool(_roots()).run(arguments)
    if not result.ok:
        raise ValueError(result.error)
    return result.data


@server.tool(name="office", meta={"copy_myself": {"risk_by_argument": {"action": {"list_apps": "read_only", "word_read_text": "read_only", "excel_list_sheets": "read_only", "excel_read_range": "read_only", "powerpoint_list_slides": "read_only", "powerpoint_read_text": "read_only"}}, "default_risk": "side_effect"}})
def office(
    action: str,
    app: str | None = None,
    path: str | None = None,
    destination: str | None = None,
    sheet: str | None = None,
    range: str | None = None,
    values: list[list[Any]] | None = None,
    text: str | None = None,
    replacement: str | None = None,
    expected_hash: str | None = None,
    visible: bool = False,
    overwrite: bool = False,
) -> dict[str, Any]:
    arguments = {key: value for key, value in locals().items() if value is not None}
    result = OfficeTool(_roots()).run(arguments)
    if not result.ok:
        raise ValueError(result.error)
    return result.data


@server.tool(name="create_tool", meta={"copy_myself": {"risk": "side_effect"}})
def create_tool(
    tool_id: str,
    name: str,
    description: str,
    source: str,
    runtime: str = "python",
    version: str = "1.0.0",
    entrypoint: str = "server.py",
    dependencies: list[str] | None = None,
    capabilities: list[str] | None = None,
    secrets: list[str] | None = None,
    filesystem_roots: list[str] | None = None,
    next_call: dict[str, Any] | None = None,
    allow_install_scripts: bool = False,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Create, validate, install, and persist one generated MCP tool.

    The source must be a complete stdio MCP server for the selected runtime.
    """
    result = GeneratedToolManager().create(
        {
            "tool_id": tool_id,
            "name": name,
            "description": description,
            "source": source,
            "runtime": runtime,
            "version": version,
            "entrypoint": entrypoint,
            "dependencies": dependencies or [],
            "capabilities": capabilities or [],
            "secrets": secrets or [],
            "filesystem_roots": filesystem_roots or [],
            "next_call": next_call,
            "allow_install_scripts": allow_install_scripts,
            "timeout_seconds": timeout_seconds,
        },
        install=True,
    )
    return result


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
