from __future__ import annotations

from typing import Protocol


class MemoryStore(Protocol):
    def save(self, role: str, content: str) -> None:
        """Persist one interaction snippet."""

    def search(self, query: str, limit: int = 5) -> list[str]:
        """Return memory snippets relevant to the query."""
