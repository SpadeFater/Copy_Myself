from __future__ import annotations

from copy_myself.agent import graph as graph_module
from copy_myself.agent.graph import build_graph, run_agent


class FakeModelClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        return "model says hi"


def test_build_graph_returns_compiled_graph() -> None:
    graph = build_graph()

    assert graph is not None


def test_run_agent_returns_response_for_chat() -> None:
    state = run_agent("请帮我整理任务")

    assert state["intent"] == "chat"
    assert state["response"]


def test_run_agent_uses_model_client_for_chat(monkeypatch) -> None:
    client = FakeModelClient()
    monkeypatch.setattr(graph_module, "build_model_client", lambda: client)

    state = run_agent("请和我聊天")

    assert state["intent"] == "chat"
    assert state["response"] == "model says hi"
    assert client.calls
    assert client.calls[0][-1]["content"] == "请和我聊天"


def test_run_agent_routes_health_check_to_tool() -> None:
    state = run_agent("health check")

    assert state["intent"] == "health_check"
    assert state["tool_result"] == {"status": "ok", "source": "agent"}
