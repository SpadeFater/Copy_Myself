from __future__ import annotations

from typing import Protocol

from copy_myself.memory.models import MemoryNode


class MemoryStore(Protocol):
    def save(self, role: str, content: str) -> None:
        """Persist one interaction snippet."""

    def search(self, query: str, limit: int = 5) -> list[str]:
        """Return memory snippets relevant to the query."""

    def save_exchange(
        self,
        user_input: str,
        assistant_response: str,
        *,
        session: str | None = None,
        source: str = "local",
    ) -> MemoryNode:
        """Persist one completed user-assistant exchange."""

    def retrieve(
        self,
        query: str,
        limit: int = 5,
        *,
        expand_relations: bool = True,
    ) -> list[MemoryNode]:
        """Return ranked durable memory nodes."""
