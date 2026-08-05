from __future__ import annotations

import asyncio

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from agent.graph import build_graph
from agent.state import create_initial_state
from agent.tool_execution import ToolExecutionCoordinator
from llm.base import ModelClient
from memory.base import MemoryStore


class AgentRunner:
    def __init__(self, memory: MemoryStore | None = None, coordinator: ToolExecutionCoordinator | None = None, model_client: ModelClient | None = None) -> None:
        self.coordinator = coordinator or ToolExecutionCoordinator()
        self.graph = build_graph(memory, self.coordinator, model_client, InMemorySaver())

    async def arun_state(self, user_input: str, session_id: str):
        await self.coordinator.client.start()
        return await self.graph.ainvoke(create_initial_state(user_input, session_id), {"configurable": {"thread_id": session_id}})

    async def resume_state(self, approved: bool, session_id: str):
        await self.coordinator.client.start()
        return await self.graph.ainvoke(Command(resume=approved), {"configurable": {"thread_id": session_id}})

    def run_state(self, user_input: str, session_id: str = "default"):
        async def run_once():
            try:
                return await self.arun_state(user_input, session_id)
            finally:
                await self.close()

        return asyncio.run(run_once())

    async def close(self) -> None:
        await self.coordinator.close()
