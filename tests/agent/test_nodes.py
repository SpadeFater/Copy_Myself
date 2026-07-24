from copy_myself.agent.nodes import (
    classify_intent,
    create_response,
    load_memory_context,
    run_selected_tool,
)
from copy_myself.agent.state import create_initial_state
from copy_myself.memory import InMemoryStore
from copy_myself.tools import HealthTool, ToolRegistry


def test_classify_intent_detects_health_check() -> None:
    state = create_initial_state("health check")

    result = classify_intent(state)

    assert result["intent"] == "health_check"
    assert result["tool_name"] == "health"


def test_classify_intent_defaults_to_chat() -> None:
    state = create_initial_state("帮我整理一下思路")

    result = classify_intent(state)

    assert result["intent"] == "chat"
    assert result["tool_name"] is None


def test_load_memory_context_reads_store() -> None:
    memory = InMemoryStore()
    memory.save("user", "项目目标是个人管家")
    state = create_initial_state("个人管家")

    result = load_memory_context(state, memory)

    assert result["memory_context"] == ["user: 项目目标是个人管家"]


def test_run_selected_tool_uses_registry() -> None:
    registry = ToolRegistry()
    registry.register(HealthTool())
    state = create_initial_state("health")
    state["tool_name"] = "health"

    result = run_selected_tool(state, registry)

    assert result["tool_result"] == {"status": "ok", "source": "agent"}
    assert result["error"] is None


def test_create_response_uses_error_fallback() -> None:
    state = create_initial_state("hello")
    state["error"] = "Tool failed"

    result = create_response(state)

    assert "暂时无法完成" in result["response"]
