from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.dependencies import create_default_memory_store
from agent.runner import AgentRunner
from llm.base import ModelClient
from memory.base import MemoryStore
from tools.registry import ToolRegistry


@dataclass(frozen=True)
class ChatRunResult:
    message: str
    response: str
    intent: str
    display_intent: str
    tool_result: dict[str, Any] | None
    memory_context: list[str]
    graph_steps: list[str]


class ChatService:
    def __init__(
        self,
        memory: MemoryStore | None = None,
        registry: ToolRegistry | None = None,
        model_client: ModelClient | None = None,
    ) -> None:
        self.memory = memory or create_default_memory_store()
        self.runner = AgentRunner(self.memory, registry, model_client)

    def chat(self, message: str) -> ChatRunResult:
        state = self.runner.run_state(message)
        tool_result = state.get("tool_result")
        display_intent = self._display_intent(state["intent"], tool_result)
        return ChatRunResult(
            message=message,
            response=state.get("response") or "",
            intent=state["intent"],
            display_intent=display_intent,
            tool_result=tool_result,
            memory_context=state.get("memory_context", []),
            graph_steps=["load_memory", "classify_intent", "run_tool", "create_response", "save_memory"],
        )

    @staticmethod
    def _display_intent(intent: str, tool_result: dict[str, Any] | None) -> str:
        if intent == "time_lookup":
            return f"时间查询 · {'getTime' if tool_result else '时间工具'}"
        if intent == "chat":
            return "对话"
        return intent
