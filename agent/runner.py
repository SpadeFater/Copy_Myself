from __future__ import annotations

from agent.graph import build_graph
from agent.state import create_initial_state
from llm.base import ModelClient
from memory.base import MemoryStore
from tools.registry import ToolRegistry


class AgentRunner:
    def __init__(
        self,
        memory: MemoryStore | None = None,
        registry: ToolRegistry | None = None,
        model_client: ModelClient | None = None,
    ) -> None:
        self.memory = memory
        self.registry = registry
        self.model_client = model_client

    def run_state(self, user_input: str):
        graph = build_graph(
            memory=self.memory,
            registry=self.registry,
            model_client=self.model_client,
        )
        return graph.invoke(create_initial_state(user_input))
