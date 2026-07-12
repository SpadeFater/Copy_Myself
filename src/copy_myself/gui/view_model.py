from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from copy_myself.agent.graph import run_agent
from copy_myself.memory import GraphMemoryStore
from copy_myself.memory.base import MemoryStore


PENDING_RESPONSE = "正在思考..."
WELCOME_MESSAGE = "你好，我是 Copy_Myself，你的个人智能管家。"


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
    memory: MemoryStore = field(default_factory=GraphMemoryStore)
    messages: list[ChatMessage] = field(default_factory=list)
    latest_run: RunSummary | None = None

    def __post_init__(self) -> None:
        if not self.messages:
            self.messages.append(self._welcome_message())

    def send_message(self, message: str) -> RunSummary | None:
        clean_message = self.begin_message(message)
        if clean_message is None:
            return None

        state = run_agent(clean_message, memory=self.memory)
        return self.complete_message(clean_message, state)

    def begin_message(self, message: str) -> str | None:
        clean_message = message.strip()
        if not clean_message:
            return None

        self.messages.append(ChatMessage(role="user", content=clean_message))
        self.messages.append(ChatMessage(role="assistant", content=PENDING_RESPONSE))
        return clean_message

    def append_response_chunk(self, chunk: str) -> str:
        if not chunk:
            return self.messages[-1].content if self.messages else ""

        pending = ChatMessage(role="assistant", content=PENDING_RESPONSE)
        if self.messages and self.messages[-1] == pending:
            self.messages[-1] = ChatMessage(role="assistant", content=chunk)
        elif self.messages and self.messages[-1].role == "assistant":
            current = self.messages[-1]
            self.messages[-1] = ChatMessage(role="assistant", content=current.content + chunk)
        else:
            self.messages.append(ChatMessage(role="assistant", content=chunk))
        return self.messages[-1].content

    def complete_message(self, clean_message: str, state: dict[str, Any]) -> RunSummary:
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
        pending = ChatMessage(role="assistant", content=PENDING_RESPONSE)
        if self.messages and self.messages[-1] == pending:
            self.messages[-1] = ChatMessage(role="assistant", content=summary.response)
        elif self.messages and self.messages[-1].role == "assistant":
            self.messages[-1] = ChatMessage(role="assistant", content=summary.response)
        else:
            self.messages.append(ChatMessage(role="assistant", content=summary.response))
        self.latest_run = summary
        return summary

    def complete_memory_items(self, limit: int = 30) -> list[str]:
        list_recent = getattr(self.memory, "list_recent", None)
        if callable(list_recent):
            return list_recent(limit=limit)
        return self.memory.search("", limit=limit)

    def plan_items(self) -> list[str]:
        if self.latest_run is None:
            return ["等待指令", "规划下一步", "执行后复盘"]

        if self.latest_run.intent == "tool":
            return ["理解请求", "选择工具", "返回工具结果"]
        if self.latest_run.intent == "health_check":
            return ["检查本地运行状态", "确认工具链可用", "汇报结果"]
        return ["理解上下文", "组织回答", "记录有用记忆"]

    def flush_memory(self) -> None:
        flush = getattr(self.memory, "flush", None)
        if callable(flush):
            flush()

    def start_new_conversation(self, session_id: str | None = None) -> str | None:
        start_new_session = getattr(self.memory, "start_new_session", None)
        new_session_id = start_new_session(session_id) if callable(start_new_session) else None
        if new_session_id is None:
            self.flush_memory()

        self.messages = [self._welcome_message()]
        self.latest_run = None
        return new_session_id

    def _welcome_message(self) -> ChatMessage:
        return ChatMessage(role="assistant", content=WELCOME_MESSAGE)
