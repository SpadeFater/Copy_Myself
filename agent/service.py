from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Literal

from agent.dependencies import create_default_memory_store
from agent.runner import AgentRunner
from agent.tool_execution import PendingApproval, ToolExecutionCoordinator
from llm.base import ModelClient
from memory.base import MemoryStore


@dataclass(frozen=True)
class ChatRunResult:
    message: str
    response: str
    intent: str
    display_intent: str
    tool_result: dict[str, Any] | None
    memory_context: list[str]
    graph_steps: list[str]
    status: Literal["completed", "pending_approval", "failed"] = "completed"
    pending_approval: PendingApproval | None = None


class ChatService:
    def __init__(self, memory: MemoryStore | None = None, coordinator: ToolExecutionCoordinator | None = None, model_client: ModelClient | None = None) -> None:
        self.runner = AgentRunner(memory or create_default_memory_store(), coordinator, model_client)
        self._pending_sessions: dict[str, str] = {}

    async def achat(self, message: str, session_id: str = "default") -> ChatRunResult:
        return self._result(message, await self.runner.arun_state(message, session_id), session_id)

    async def resume(self, approval_id: str, approved: bool, session_id: str) -> ChatRunResult:
        if self._pending_sessions.get(approval_id) != session_id:
            return self._failed("approval_session_mismatch")
        del self._pending_sessions[approval_id]
        return self._result("", await self.runner.resume_state(approved, session_id), session_id)

    def chat(self, message: str, session_id: str = "default") -> ChatRunResult:
        async def run_once() -> ChatRunResult:
            try:
                return await self.achat(message, session_id)
            finally:
                await self.runner.close()

        return asyncio.run(run_once())

    def _result(self, message: str, state: dict[str, Any], session_id: str) -> ChatRunResult:
        interrupts = state.get("__interrupt__", ())
        pending = PendingApproval(**interrupts[0].value) if interrupts else None
        if pending:
            self._pending_sessions[pending.approval_id] = session_id
        result = state.get("tool_result")
        intent = state.get("intent", "chat")
        status = "pending_approval" if pending else ("failed" if state.get("error") else "completed")
        return ChatRunResult(message, state.get("response") or "", intent, self._display_intent(intent), result, state.get("memory_context", []), ["load_memory", "classify_intent", "select_tool", "run_tool", "create_response", "save_memory"], status, pending)

    @staticmethod
    def _failed(code: str) -> ChatRunResult:
        return ChatRunResult("", code, "chat", "chat", None, [], [], "failed")

    @staticmethod
    def _display_intent(intent: str) -> str:
        return "time lookup / builtin__getTime" if intent == "time_lookup" else "chat"
