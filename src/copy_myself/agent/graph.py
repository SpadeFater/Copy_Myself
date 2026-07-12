from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from langgraph.graph import END, StateGraph

from copy_myself.agent.nodes import (
    classify_intent,
    create_response,
    load_memory_context,
    run_selected_tool,
)
from copy_myself.agent.state import ButlerState, create_initial_state
from copy_myself.memory import InMemoryStore
from copy_myself.memory.base import MemoryStore
from copy_myself.model_adapter import ChatResponder, build_default_responder
from copy_myself.tools import ToolRegistry


@dataclass(frozen=True)
class AgentStreamEvent:
    kind: Literal["chunk", "done"]
    content: str = ""
    state: ButlerState | None = None


def build_default_registry() -> ToolRegistry:
    return ToolRegistry(discover=True)


class MyAgent:
    """Small runtime wrapper for model, memory, tools, and graph execution."""

    def __init__(
        self,
        memory: MemoryStore | None = None,
        registry: ToolRegistry | None = None,
        responder: ChatResponder | None = None,
    ) -> None:
        self.memory = memory or InMemoryStore()
        self.registry = registry or build_default_registry()
        self.responder = responder or build_default_responder()
        self.graph = build_graph(
            memory=self.memory,
            registry=self.registry,
            responder=self.responder,
        )

    def import_memory_file(self, file_path: str | Path, role: str = "memory") -> int:
        path = Path(file_path)
        if not path.exists():
            return 0

        imported_count = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            content = line.strip()
            if not content:
                continue
            self.memory.save(role, content)
            imported_count += 1
        return imported_count

    def run(self, user_input: str) -> ButlerState:
        state = self.graph.invoke(create_initial_state(user_input))
        response = state.get("response")
        if response:
            self._save_interaction(user_input, response)
        return state

    def stream(self, user_input: str):
        state = create_initial_state(user_input)
        state = load_memory_context(state, self.memory)
        state = classify_intent(state, self.registry, self.responder)
        state = run_selected_tool(state, self.registry)

        if state.get("tool_result") or state.get("error"):
            state = create_response(state, self.responder)
            response = state.get("response")
            if response:
                self._save_interaction(user_input, response)
            yield AgentStreamEvent(kind="done", state=state)
            return

        chunks: list[str] = []
        stream_method = getattr(self.responder, "stream", None)
        if callable(stream_method):
            for chunk in stream_method(user_input, state.get("memory_context", [])):
                if not chunk:
                    continue
                chunks.append(chunk)
                yield AgentStreamEvent(kind="chunk", content=chunk)
        else:
            response = self.responder.generate(user_input, state.get("memory_context", []))
            chunks.append(response)
            yield AgentStreamEvent(kind="chunk", content=response)

        state["response"] = "".join(chunks)
        if state["response"]:
            self._save_interaction(user_input, state["response"])
        yield AgentStreamEvent(kind="done", state=state)

    def _save_interaction(self, user_input: str, response: str) -> None:
        save_turn = getattr(self.memory, "save_turn", None)
        if callable(save_turn):
            save_turn(user_input, response, {"source": "agent"})
            return
        self.memory.save("user", user_input)
        self.memory.save("assistant", response)


def build_graph(
    memory: MemoryStore | None = None,
    registry: ToolRegistry | None = None,
    responder: ChatResponder | None = None,
):
    memory_store = memory or InMemoryStore()
    tool_registry = registry or build_default_registry()
    chat_responder = responder or build_default_responder()

    graph = StateGraph(ButlerState)
    graph.add_node("load_memory", lambda state: load_memory_context(state, memory_store))
    graph.add_node("classify_intent", lambda state: classify_intent(state, tool_registry, chat_responder))
    graph.add_node("run_tool", lambda state: run_selected_tool(state, tool_registry))
    graph.add_node("create_response", lambda state: create_response(state, chat_responder))

    graph.set_entry_point("load_memory")
    graph.add_edge("load_memory", "classify_intent")
    graph.add_edge("classify_intent", "run_tool")
    graph.add_edge("run_tool", "create_response")
    graph.add_edge("create_response", END)
    return graph.compile()


def run_agent(
    user_input: str,
    memory: MemoryStore | None = None,
    registry: ToolRegistry | None = None,
    responder: ChatResponder | None = None,
) -> ButlerState:
    agent = MyAgent(memory=memory, registry=registry, responder=responder)
    return agent.run(user_input)


def stream_agent(
    user_input: str,
    memory: MemoryStore | None = None,
    registry: ToolRegistry | None = None,
    responder: ChatResponder | None = None,
):
    agent = MyAgent(memory=memory, registry=registry, responder=responder)
    yield from agent.stream(user_input)
