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
    session_id: str
    tool_definitions: list[dict[str, Any]]


def create_initial_state(user_input: str, session_id: str = "default") -> ButlerState:
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
        "session_id": session_id,
        "tool_definitions": [],
    }
