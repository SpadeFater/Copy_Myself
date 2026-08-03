from agent.nodes import (
    classify_intent,
    create_response,
    load_memory_context,
    run_selected_tool,
)
from agent.state import create_initial_state
from memory import InMemoryStore
from tools import TimeTool, ToolRegistry


def test_classify_intent_detects_time_lookup() -> None:
    state = create_initial_state("what time is it?")

    result = classify_intent(state)

    assert result["intent"] == "time_lookup"
    assert result["tool_name"] == "getTime"


def test_classify_intent_does_not_keep_health_alias() -> None:
    state = create_initial_state("health check")

    result = classify_intent(state)

    assert result["intent"] == "chat"
    assert result["tool_name"] is None


def test_classify_intent_defaults_to_chat() -> None:
    state = create_initial_state("帮我整理一下思路")

    result = classify_intent(state)

    assert result["intent"] == "chat"
    assert result["tool_name"] is None


def test_classify_intent_extracts_timezone_for_time_request() -> None:
    state = create_initial_state("what time is it in Asia/Shanghai?")

    result = classify_intent(state)

    assert result["intent"] == "time_lookup"
    assert result["tool_name"] == "getTime"
    assert result["tool_arguments"] == {"timezone": "Asia/Shanghai"}


def test_classify_intent_routes_explicit_file_listing_to_filesystem() -> None:
    state = create_initial_state("list files")

    result = classify_intent(state)

    assert result["intent"] == "chat"
    assert result["tool_name"] == "filesystem"
    assert result["tool_arguments"] == {"action": "list", "path": "."}


def test_load_memory_context_reads_store() -> None:
    memory = InMemoryStore()
    memory.save("user", "项目目标是个人管家")
    state = create_initial_state("个人管家")

    result = load_memory_context(state, memory)

    assert result["memory_context"] == ["user: 项目目标是个人管家"]


def test_run_selected_tool_uses_registry() -> None:
    registry = ToolRegistry()
    registry.register(TimeTool())
    state = create_initial_state("what time is it in UTC?")
    state["tool_name"] = "getTime"
    state["tool_arguments"] = {"timezone": "UTC"}

    result = run_selected_tool(state, registry)

    assert result["tool_result"]["status"] == "ok"
    assert result["tool_result"]["timezone"] == "UTC"
    assert result["tool_result"]["source"] == "agent"
    assert result["error"] is None


def test_create_response_uses_error_fallback() -> None:
    state = create_initial_state("hello")
    state["error"] = "Tool failed"

    result = create_response(state)

    assert "暂时无法完成" in result["response"]


def test_create_response_formats_time_result_as_butler_message() -> None:
    state = create_initial_state("现在几点")
    state["intent"] = "time_lookup"
    state["tool_name"] = "getTime"
    state["tool_result"] = {
        "status": "ok",
        "time": "2026-07-25T18:30:00+08:00",
        "timezone": "Asia/Shanghai",
    }

    result = create_response(state)

    assert result["response"] == (
        "好的，我已经帮你查好了。\n\n"
        "当前时间：2026-07-25 18:30:00\n"
        "时区：Asia/Shanghai"
    )
