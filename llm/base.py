from __future__ import annotations

from typing import Any, Protocol, TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str


class ToolDecision(TypedDict):
    tool_call: dict[str, Any] | None
    content: str | None


class ModelClient(Protocol):
    def complete(self, messages: list[ChatMessage]) -> str:
        """Return assistant text for the provided message list."""
