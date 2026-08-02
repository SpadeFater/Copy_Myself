from __future__ import annotations

from copy_myself.agent import graph as graph_module
from copy_myself.agent.graph import build_graph, run_agent
from copy_myself.memory import GraphMemoryStore


class FakeModelClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        return "model says hi"


def test_build_graph_returns_compiled_graph(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COPY_MYSELF_MEMORY_PATH", str(tmp_path / "memory.sqlite3"))
    graph = build_graph()

    assert graph is not None


def test_run_agent_returns_response_for_chat() -> None:
    state = run_agent("请帮我整理任务", memory=GraphMemoryStore(":memory:"))

    assert state["intent"] == "chat"
    assert state["response"]


def test_run_agent_uses_model_client_for_chat(monkeypatch) -> None:
    client = FakeModelClient()
    monkeypatch.setattr(graph_module, "build_model_client", lambda: client)

    state = run_agent("请和我聊天", memory=GraphMemoryStore(":memory:"))

    assert state["intent"] == "chat"
    assert state["response"] == "model says hi"
    assert client.calls
    assert client.calls[0][-1]["content"] == "请和我聊天"


def test_run_agent_routes_time_lookup_to_tool() -> None:
    state = run_agent("what time is it in Asia/Shanghai?", memory=GraphMemoryStore(":memory:"))

    assert state["intent"] == "time_lookup"
    assert state["tool_name"] == "getTime"
    assert state["tool_result"]["status"] == "ok"
    assert state["tool_result"]["timezone"] == "Asia/Shanghai"


def test_graph_saves_interaction_in_memory_node() -> None:
    memory = GraphMemoryStore(":memory:")
    graph = build_graph(memory=memory)

    assert "save_memory" in graph.get_graph().nodes

    run_agent("请记住我喜欢早晨工作", memory=memory)

    records = memory.list_nodes()
    assert len(records) == 1
    assert records[0].user_input == "请记住我喜欢早晨工作"
    assert records[0].assistant_response


def test_run_agent_defaults_to_persistent_graph_memory(tmp_path, monkeypatch) -> None:
    memory_path = tmp_path / "memory.sqlite3"
    monkeypatch.setenv("COPY_MYSELF_MEMORY_PATH", str(memory_path))

    run_agent("Please remember that I prefer concise Chinese.")

    store = GraphMemoryStore(memory_path)
    records = store.list_nodes()
    assert len(records) == 1
    assert records[0].user_input == "Please remember that I prefer concise Chinese."
