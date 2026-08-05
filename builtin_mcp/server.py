from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from builtin_mcp.tools.filesystem import FileSystemTool
from builtin_mcp.tools.time import TimeTool


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


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
