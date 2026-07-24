from __future__ import annotations

from langgraph.graph import END, StateGraph

from copy_myself.config import load_settings
from copy_myself.agent.nodes import (
    classify_intent,
    create_response,
    load_memory_context,
    run_selected_tool,
)
from copy_myself.agent.state import ButlerState, create_initial_state
from copy_myself.memory import InMemoryStore
from copy_myself.memory.base import MemoryStore
from copy_myself.llm.base import ModelClient
from copy_myself.llm.openai_compatible import OpenAICompatibleClient
from copy_myself.tools import HealthTool, ToolRegistry


def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(HealthTool())
    return registry


def build_model_client() -> ModelClient | None:
    settings = load_settings()
    for provider in settings.model.providers:
        if provider.enabled:
            return OpenAICompatibleClient(provider)
    return None


def build_graph(
    memory: MemoryStore | None = None,
    registry: ToolRegistry | None = None,
    model_client: ModelClient | None = None,
):
    memory_store = memory or InMemoryStore()
    tool_registry = registry or create_default_registry()
    active_model_client = model_client if model_client is not None else build_model_client()

    graph = StateGraph(ButlerState)
    graph.add_node("load_memory", lambda state: load_memory_context(state, memory_store))
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("run_tool", lambda state: run_selected_tool(state, tool_registry))
    graph.add_node(
        "create_response",
        lambda state: create_response(state, model_client=active_model_client),
    )

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
    model_client: ModelClient | None = None,
) -> ButlerState:
    graph = build_graph(memory=memory, registry=registry, model_client=model_client)
    state = graph.invoke(create_initial_state(user_input))
    response = state.get("response")
    if response:
        target_memory = memory
        if target_memory is not None:
            target_memory.save("user", user_input)
            target_memory.save("assistant", response)
    return state
