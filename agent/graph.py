from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.dependencies import build_model_client, create_default_memory_store
from agent.nodes import classify_intent, create_response, load_memory_context, run_selected_tool, save_memory_context, select_model_tool
from agent.state import ButlerState
from agent.tool_execution import ToolExecutionCoordinator
from llm.base import ModelClient
from memory.base import MemoryStore


def build_graph(memory: MemoryStore | None = None, coordinator: ToolExecutionCoordinator | None = None, model_client: ModelClient | None = None, checkpointer=None):
    memory_store = memory or create_default_memory_store()
    tools = coordinator or ToolExecutionCoordinator()
    model = model_client if model_client is not None else build_model_client()
    graph = StateGraph(ButlerState)
    async def load_memory(state):
        return load_memory_context(state, memory_store)

    async def classify(state):
        return classify_intent(state)

    async def respond(state):
        return create_response(state, model)

    async def select(state):
        return await select_model_tool(state, model, tools)

    async def run_tool(state):
        return await run_selected_tool(state, tools)

    async def save_memory(state):
        return save_memory_context(state, memory_store)

    graph.add_node("load_memory", load_memory)
    graph.add_node("classify_intent", classify)
    graph.add_node("select_tool", select)
    graph.add_node("run_tool", run_tool)
    graph.add_node("create_response", respond)
    graph.add_node("save_memory", save_memory)
    graph.set_entry_point("load_memory")
    for source, target in (("load_memory", "classify_intent"), ("classify_intent", "select_tool"), ("select_tool", "run_tool"), ("run_tool", "create_response"), ("create_response", "save_memory"), ("save_memory", END)):
        graph.add_edge(source, target)
    return graph.compile(checkpointer=checkpointer)


def run_agent(user_input: str, memory: MemoryStore | None = None, model_client: ModelClient | None = None) -> ButlerState:
    from agent.runner import AgentRunner

    return AgentRunner(memory=memory, model_client=model_client).run_state(user_input)
