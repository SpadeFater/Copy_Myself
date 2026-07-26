from datetime import datetime

from copy_myself.tools import TimeTool, ToolRegistry


def test_registry_runs_registered_tool() -> None:
    registry = ToolRegistry()
    registry.register(TimeTool())

    result = registry.run("getTime", {"source": "test", "timezone": "UTC"})

    assert result.name == "getTime"
    assert result.ok is True
    assert result.data["status"] == "ok"
    assert result.data["source"] == "test"
    assert result.data["timezone"] == "UTC"
    assert datetime.fromisoformat(result.data["time"]).tzinfo is not None


def test_health_tool_accepts_location_alias() -> None:
    result = TimeTool().run({"location": "Beijing"})

    assert result.ok is True
    assert result.data["timezone"] == "Asia/Shanghai"
    assert datetime.fromisoformat(result.data["time"]).utcoffset().total_seconds() == 8 * 3600


def test_health_tool_reports_invalid_timezone() -> None:
    result = TimeTool().run({"timezone": "Not/AZone"})

    assert result.ok is False
    assert "Unknown timezone" in result.error


def test_registry_reports_missing_tool() -> None:
    registry = ToolRegistry()

    result = registry.run("missing", {})

    assert result.name == "missing"
    assert result.ok is False
    assert "not registered" in result.error
