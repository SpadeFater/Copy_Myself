from __future__ import annotations

from typing import Protocol, TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str


class ModelClient(Protocol):
    def complete(self, messages: list[ChatMessage]) -> str:
        """Return assistant text for the provided message list."""
