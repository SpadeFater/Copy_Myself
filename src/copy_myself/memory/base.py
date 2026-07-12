from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MemoryRecord:
    role: str
    content: str
    created_at: str
    session_id: str

    def format(self) -> str:
        return f"{self.role}: {self.content}"


@dataclass(frozen=True)
class MemoryNode:
    id: str
    session_id: str
    created_at: str
    updated_at: str
    user_input: str
    assistant_response: str
    summary: str
    preference_memory: list[str]
    project_memory: list[str]
    task_memory: list[str]
    episode_memory: list[str]
    tags: list[str]
    project: str | None
    task_id: str | None
    importance: float
    confidence: float
    embedding: list[float] | None
    source: str

    def format(self) -> str:
        if self.assistant_response:
            return f"user: {self.user_input} | assistant: {self.assistant_response}"
        return f"user: {self.user_input}"


@dataclass(frozen=True)
class MemoryEdge:
    id: str
    from_node_id: str
    to_node_id: str
    relation: str
    weight: float
    reason: str
    created_at: str


class MemoryStore(Protocol):
    def save(self, role: str, content: str) -> None:
        """Persist one interaction snippet."""

    def search(self, query: str, limit: int = 5) -> list[str]:
        """Return memory snippets relevant to the query."""

    def save_turn(self, user_input: str, assistant_response: str, metadata: dict[str, str] | None = None) -> str:
        """Persist one completed user-assistant exchange."""

    def retrieve_nodes(self, query: str, limit: int = 5) -> list[MemoryNode]:
        """Return memory nodes relevant to the query."""

    def list_recent(self, limit: int = 20) -> list[str]:
        """Return recent complete memory records for user display."""

    def get_brief_context(self, query: str = "") -> list[str]:
        """Return compact memory snippets for model context."""
