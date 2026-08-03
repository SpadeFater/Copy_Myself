from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from agent.dependencies import create_default_memory_store
from memory.base import MemoryStore


@dataclass
class WorkbenchSession:
    session_id: str
    memory: MemoryStore = field(default_factory=create_default_memory_store)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, WorkbenchSession] = {}

    def get_or_create(self, session_id: str | None = None) -> WorkbenchSession:
        key = session_id or uuid4().hex
        if key not in self._sessions:
            self._sessions[key] = WorkbenchSession(session_id=key)
        return self._sessions[key]
