from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from copy_myself.agent.graph import create_default_memory_store, run_agent
from copy_myself.memory.base import MemoryStore


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class RunSummary:
    message: str
    response: str
    intent: str
    display_intent: str
    stage_label: str
    tool_result: dict[str, Any] | None
    memory_context: list[str]
    graph_steps: list[str]


@dataclass
class WorkbenchViewModel:
    memory: MemoryStore = field(default_factory=create_default_memory_store)
    messages: list[ChatMessage] = field(default_factory=list)
    latest_run: RunSummary | None = None

    def _display_intent(self, intent: str, tool_result: dict[str, Any] | None) -> str:
        if intent == "time_lookup":
            tool_name = "getTime" if tool_result else "时间工具"
            return f"时间查询 · {tool_name}"
        if intent == "chat":
            return "对话"
        return intent

    def __post_init__(self) -> None:
        if not self.messages:
            self.messages.append(
                ChatMessage(
                    role="assistant",
                    content="Copy_Myself personal butler is ready.",
                )
            )

    def send_message(self, message: str) -> RunSummary | None:
        clean_message = message.strip()
        if not clean_message:
            return None

        self.messages.append(ChatMessage(role="user", content=clean_message))
        state = run_agent(clean_message, memory=self.memory)
        summary = RunSummary(
            message=clean_message,
            response=state.get("response") or "",
            intent=state["intent"],
            display_intent=self._display_intent(state["intent"], state.get("tool_result")),
            stage_label=self._display_intent(state["intent"], state.get("tool_result")),
            tool_result=state.get("tool_result"),
            memory_context=state.get("memory_context", []),
            graph_steps=[
                "load_memory",
                "classify_intent",
                "run_tool",
                "create_response",
                "save_memory",
            ],
        )
        self.messages.append(ChatMessage(role="assistant", content=summary.response))
        self.latest_run = summary
        return summary
