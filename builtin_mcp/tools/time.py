from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from builtin_mcp.tools.base import ToolResult


LOCATION_TIMEZONES = {
    "beijing": "Asia/Shanghai",
    "中国": "Asia/Shanghai",
    "上海": "Asia/Shanghai",
    "new york": "America/New_York",
    "纽约": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "洛杉矶": "America/Los_Angeles",
    "london": "Europe/London",
    "伦敦": "Europe/London",
    "tokyo": "Asia/Tokyo",
    "东京": "Asia/Tokyo",
}


def resolve_timezone(arguments: dict[str, Any]) -> tuple[str, Any]:
    requested = arguments.get("timezone") or arguments.get("location")
    if requested is None or not str(requested).strip():
        local_now = datetime.now().astimezone()
        timezone_name = getattr(local_now.tzinfo, "key", local_now.tzname() or "local")
        return timezone_name, local_now.tzinfo

    value = str(requested).strip()
    timezone_name = LOCATION_TIMEZONES.get(value.casefold(), value)
    try:
        return timezone_name, ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone or location: {value}") from exc


class TimeTool:
    name = "getTime"
    description = "Returns the current time for an IANA timezone or supported location."
    parameters = {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "IANA timezone such as Asia/Shanghai or UTC.",
            },
            "location": {
                "type": "string",
                "description": "Supported city or location name.",
            },
        },
        "additionalProperties": False,
    }

    def run(self, arguments: dict[str, Any]) -> ToolResult:
        try:
            timezone_name, timezone = resolve_timezone(arguments)
            current_time = datetime.now(timezone).isoformat(timespec="seconds")
        except ValueError as exc:
            return ToolResult(name=self.name, ok=False, error=str(exc))

        return ToolResult(
            name=self.name,
            ok=True,
            data={
                "status": "ok",
                "source": arguments.get("source", "agent"),
                "time": current_time,
                "timezone": timezone_name,
            },
        )
