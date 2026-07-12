from copy_myself.agent.nodes import (
    classify_intent,
    create_response,
    load_memory_context,
    run_selected_tool,
)
from copy_myself.agent.state import create_initial_state
from copy_myself.memory import InMemoryStore
from copy_myself.tools import HealthTool, LocalTool, ToolRegistry, ToolResult


class FakeToolRouter:
    def generate(self, user_input: str, memory_context: list[str]) -> str:
        assert "calendar" in user_input
        assert "schedule a meeting tomorrow at 10" in user_input
        return '{"tool_name": "calendar", "arguments": {"title": "meeting", "time": "tomorrow at 10"}}'


class CalendarTool(LocalTool):
    name = "calendar"
    description = "Create calendar events for meetings and schedules."

    def run(self, arguments):
        return ToolResult(name=self.name, ok=True, data={"created": arguments})


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


def test_classify_intent_uses_model_to_select_registered_tool() -> None:
    registry = ToolRegistry(discover=False)
    registry.register(CalendarTool())
    state = create_initial_state("schedule a meeting tomorrow at 10")

    result = classify_intent(state, registry=registry, responder=FakeToolRouter())

    assert result["intent"] == "tool"
    assert result["tool_name"] == "calendar"
    assert result["tool_arguments"] == {"title": "meeting", "time": "tomorrow at 10"}


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


def test_run_selected_tool_passes_model_arguments_to_tool() -> None:
    registry = ToolRegistry(discover=False)
    registry.register(CalendarTool())
    state = create_initial_state("schedule a meeting tomorrow at 10")
    state["tool_name"] = "calendar"
    state["tool_arguments"] = {"title": "meeting", "time": "tomorrow at 10"}

    result = run_selected_tool(state, registry)

    assert result["tool_result"] == {
        "created": {"source": "agent", "title": "meeting", "time": "tomorrow at 10"}
    }
    assert result["error"] is None


def test_load_memory_context_prefers_brief_memory_when_available() -> None:
    class BriefMemory:
        def save(self, role: str, content: str) -> None:
            raise AssertionError("not used")

        def search(self, query: str, limit: int = 5) -> list[str]:
            raise AssertionError("brief memory should be preferred")

        def get_brief_context(self) -> list[str]:
            return ["- 用户喜欢短回答", "- 项目是个人管家"]

    state = create_initial_state("继续")

    result = load_memory_context(state, BriefMemory())

    assert result["memory_context"] == ["- 用户喜欢短回答", "- 项目是个人管家"]


def test_create_response_uses_error_fallback() -> None:
    state = create_initial_state("hello")
    state["error"] = "Tool failed"

    result = create_response(state)

    assert "暂时无法完成" in result["response"]


def test_load_memory_context_passes_query_when_supported() -> None:
    class QueryAwareMemory:
        def __init__(self) -> None:
            self.query = ""

        def save(self, role: str, content: str) -> None:
            raise AssertionError("not used")

        def search(self, query: str, limit: int = 5) -> list[str]:
            raise AssertionError("query-aware brief context should be preferred")

        def get_brief_context(self, query: str = "") -> list[str]:
            self.query = query
            return [f"query: {query}"]

    state = create_initial_state("继续实现 memory graph")
    memory = QueryAwareMemory()

    result = load_memory_context(state, memory)

    assert memory.query == "继续实现 memory graph"
    assert result["memory_context"] == ["query: 继续实现 memory graph"]
