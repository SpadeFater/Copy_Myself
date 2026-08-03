from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.dependencies import create_default_memory_store
from agent.service import ChatService
from memory.base import MemoryStore


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
        result = ChatService(memory=self.memory).chat(clean_message)
        summary = RunSummary(
            message=clean_message,
            response=result.response,
            intent=result.intent,
            display_intent=result.display_intent,
            stage_label=result.display_intent,
            tool_result=result.tool_result,
            memory_context=result.memory_context,
            graph_steps=result.graph_steps,
        )
        self.messages.append(ChatMessage(role="assistant", content=summary.response))
        self.latest_run = summary
        return summary
