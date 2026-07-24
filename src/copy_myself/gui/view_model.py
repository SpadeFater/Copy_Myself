from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from copy_myself.agent.graph import run_agent
from copy_myself.memory import InMemoryStore
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
    tool_result: dict[str, Any] | None
    memory_context: list[str]
    graph_steps: list[str]


@dataclass
class WorkbenchViewModel:
    memory: MemoryStore = field(default_factory=InMemoryStore)
    messages: list[ChatMessage] = field(default_factory=list)
    latest_run: RunSummary | None = None

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
            tool_result=state.get("tool_result"),
            memory_context=state.get("memory_context", []),
            graph_steps=[
                "load_memory",
                "classify_intent",
                "run_tool",
                "create_response",
            ],
        )
        self.messages.append(ChatMessage(role="assistant", content=summary.response))
        self.latest_run = summary
        return summary
