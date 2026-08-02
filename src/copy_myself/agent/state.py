from __future__ import annotations

from typing import Any, Literal, TypedDict


Intent = Literal["unknown", "chat", "time_lookup"]


class ButlerState(TypedDict):
    """Shared state passed between LangGraph nodes."""

    user_input: str
    messages: list[dict[str, str]]
    intent: Intent
    tool_name: str | None
    tool_arguments: dict[str, Any]
    tool_result: dict[str, Any] | None
    memory_context: list[str]
    response: str | None
    error: str | None


def create_initial_state(user_input: str) -> ButlerState:
    return {
        "user_input": user_input,
        "messages": [],
        "intent": "unknown",
        "tool_name": None,
        "tool_arguments": {},
        "tool_result": None,
        "memory_context": [],
        "response": None,
        "error": None,
    }
