from copy_myself.agent.graph import MyAgent, build_graph, run_agent, stream_agent
from copy_myself.memory import InMemoryStore


class FakeResponder:
    def generate(self, user_input: str, memory_context: list[str]) -> str:
        memory = memory_context[0] if memory_context else "no memory"
        return f"model says: {user_input} / {memory}"


class FakeStreamingResponder:
    def generate(self, user_input: str, memory_context: list[str]) -> str:
        return "unused"

    def stream(self, user_input: str, memory_context: list[str]):
        yield "hello"
        yield " "
        yield "stream"


def test_build_graph_returns_compiled_graph() -> None:
    graph = build_graph()

    assert graph is not None


def test_run_agent_returns_response_for_chat() -> None:
    state = run_agent("帮我整理任务")

    assert state["intent"] == "chat"
    assert state["response"]


def test_run_agent_routes_health_check_to_tool() -> None:
    state = run_agent("health check")

    assert state["intent"] == "health_check"
    assert state["tool_result"] == {"status": "ok", "source": "agent"}


def test_my_agent_saves_conversation_to_memory() -> None:
    store = InMemoryStore()
    agent = MyAgent(memory=store)

    agent.run("整理今天计划")

    results = store.search("", limit=5)
    assert results[0] == "user: 整理今天计划"
    assert results[1].startswith("assistant: ")


def test_my_agent_uses_responder_for_chat_response() -> None:
    store = InMemoryStore()
    store.save("memory", "hello brief answers")
    agent = MyAgent(memory=store, responder=FakeResponder())

    state = agent.run("hello")

    assert state["response"] == "model says: hello / memory: hello brief answers"


def test_my_agent_imports_text_memory_file(tmp_path) -> None:
    memory_file = tmp_path / "self.txt"
    memory_file.write_text("喜欢早上复盘项目\n\n正在开发个人管家\n", encoding="utf-8")
    store = InMemoryStore()
    agent = MyAgent(memory=store)

    imported_count = agent.import_memory_file(memory_file)

    assert imported_count == 2
    assert store.search("", limit=5) == [
        "memory: 喜欢早上复盘项目",
        "memory: 正在开发个人管家",
    ]


def test_stream_agent_yields_chunks_then_done_and_saves_memory() -> None:
    store = InMemoryStore()

    events = list(stream_agent("hello", memory=store, responder=FakeStreamingResponder()))

    assert [event.kind for event in events] == ["chunk", "chunk", "chunk", "done"]
    assert [event.content for event in events[:3]] == ["hello", " ", "stream"]
    assert events[-1].state is not None
    assert events[-1].state["response"] == "hello stream"
    assert store.search("", limit=5) == ["user: hello", "assistant: hello stream"]


def test_my_agent_prefers_turn_memory_when_supported() -> None:
    class TurnMemory:
        def __init__(self) -> None:
            self.turns: list[tuple[str, str, dict[str, str]]] = []

        def save(self, role: str, content: str) -> None:
            raise AssertionError("save_turn should be preferred")

        def save_turn(self, user_input: str, assistant_response: str, metadata: dict[str, str]) -> str:
            self.turns.append((user_input, assistant_response, metadata))
            return "node-a"

        def search(self, query: str, limit: int = 5) -> list[str]:
            return []

        def get_brief_context(self) -> list[str]:
            return []

    memory = TurnMemory()
    agent = MyAgent(memory=memory, responder=FakeResponder())

    agent.run("hello")

    assert memory.turns == [
        ("hello", "model says: hello / no memory", {"source": "agent"})
    ]
