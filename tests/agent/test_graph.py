from __future__ import annotations

from agent import graph as graph_module
from agent.graph import build_graph, run_agent
from memory import GraphMemoryStore
from tools import ToolRegistry
from tools.filesystem import FileSystemTool


class FakeModelClient:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        return "model says hi"


class FakeToolCallingModelClient:
    def __init__(self) -> None:
        self.tools: list[dict] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        return "unused"

    def decide(self, messages: list[dict[str, str]], tools: list[dict]) -> dict:
        self.tools = tools
        return {
            "tool_call": {"name": "filesystem", "arguments": {"action": "list", "path": "."}},
            "content": None,
        }


class FakeResumeAdviceModelClient:
    def __init__(self) -> None:
        self.complete_messages: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.complete_messages.append(messages)
        return "建议补强 Python 项目、数据库和面试算法。"

    def decide(self, messages: list[dict[str, str]], tools: list[dict]) -> dict:
        return {
            "tool_call": {"name": "filesystem", "arguments": {"action": "read", "path": "resume.txt"}},
            "content": None,
        }


def test_build_graph_returns_compiled_graph(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COPY_MYSELF_MEMORY_PATH", str(tmp_path / "memory.sqlite3"))
    graph = build_graph()

    assert graph is not None


def test_run_agent_returns_response_for_chat() -> None:
    state = run_agent("please organize my tasks", memory=GraphMemoryStore(":memory:"))

    assert state["intent"] == "chat"
    assert state["response"]


def test_run_agent_uses_model_client_for_chat(monkeypatch) -> None:
    client = FakeModelClient()
    monkeypatch.setattr(graph_module, "build_model_client", lambda: client)

    state = run_agent("please chat with me", memory=GraphMemoryStore(":memory:"))

    assert state["intent"] == "chat"
    assert state["response"] == "model says hi"
    assert client.calls
    assert client.calls[0][-1]["content"] == "please chat with me"


def test_run_agent_lets_model_call_filesystem_tool() -> None:
    client = FakeToolCallingModelClient()

    state = run_agent(
        "inspect the workspace through an available tool",
        memory=GraphMemoryStore(":memory:"),
        model_client=client,
    )

    assert state["intent"] == "chat"
    assert state["tool_name"] == "filesystem"
    assert state["tool_result"]["action"] == "list"
    assert any(tool["function"]["name"] == "filesystem" for tool in client.tools)


def test_run_agent_uses_filesystem_result_for_final_model_response(tmp_path) -> None:
    (tmp_path / "resume.txt").write_text("田恒佳\nPython 后端工程师", encoding="utf-8")
    registry = ToolRegistry()
    registry.register(FileSystemTool([tmp_path]))
    client = FakeResumeAdviceModelClient()

    state = run_agent(
        "read my resume and give study advice",
        memory=GraphMemoryStore(":memory:"),
        registry=registry,
        model_client=client,
    )

    assert state["tool_name"] == "filesystem"
    assert state["tool_result"]["action"] == "read"
    assert state["response"] == "建议补强 Python 项目、数据库和面试算法。"
    assert "田恒佳" in client.complete_messages[0][-1]["content"]


def test_run_agent_routes_explicit_file_listing_without_model() -> None:
    state = run_agent("list files", memory=GraphMemoryStore(":memory:"))

    assert state["intent"] == "chat"
    assert state["tool_name"] == "filesystem"
    assert state["tool_result"]["action"] == "list"


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

    run_agent("remember that I prefer morning focus work", memory=memory)

    records = memory.list_nodes()
    assert len(records) == 1
    assert records[0].user_input == "remember that I prefer morning focus work"
    assert records[0].assistant_response


def test_run_agent_defaults_to_persistent_graph_memory(tmp_path, monkeypatch) -> None:
    memory_path = tmp_path / "memory.sqlite3"
    monkeypatch.setenv("COPY_MYSELF_MEMORY_PATH", str(memory_path))

    run_agent("Please remember that I prefer concise Chinese.")

    store = GraphMemoryStore(memory_path)
    records = store.list_nodes()
    assert len(records) == 1
    assert records[0].user_input == "Please remember that I prefer concise Chinese."
