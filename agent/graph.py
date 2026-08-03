from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.dependencies import (
    build_model_client,
    create_default_memory_store,
    create_default_registry,
    default_filesystem_roots,
    default_memory_path,
)
from agent.intent import classify_intent
from agent.memory_steps import load_memory_context, save_memory_context
from agent.response import create_response
from agent.state import ButlerState
from agent.tool_use import run_selected_tool
from llm.base import ModelClient
from memory.base import MemoryStore
from tools.registry import ToolRegistry


def build_graph(
    memory: MemoryStore | None = None,
    registry: ToolRegistry | None = None,
    model_client: ModelClient | None = None,
):
    memory_store = memory or create_default_memory_store()
    tool_registry = registry or create_default_registry()
    active_model_client = model_client if model_client is not None else build_model_client()

    graph = StateGraph(ButlerState)
    graph.add_node("load_memory", lambda state: load_memory_context(state, memory_store))
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("run_tool", lambda state: run_selected_tool(state, tool_registry))
    graph.add_node(
        "create_response",
        lambda state: create_response(state, model_client=active_model_client, registry=tool_registry),
    )
    graph.add_node("save_memory", lambda state: save_memory_context(state, memory_store))

    graph.set_entry_point("load_memory")
    graph.add_edge("load_memory", "classify_intent")
    graph.add_edge("classify_intent", "run_tool")
    graph.add_edge("run_tool", "create_response")
    graph.add_edge("create_response", "save_memory")
    graph.add_edge("save_memory", END)
    return graph.compile()


def run_agent(
    user_input: str,
    memory: MemoryStore | None = None,
    registry: ToolRegistry | None = None,
    model_client: ModelClient | None = None,
) -> ButlerState:
    from agent.runner import AgentRunner

    return AgentRunner(
        memory=memory,
        registry=registry,
        model_client=model_client,
    ).run_state(user_input)
