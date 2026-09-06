from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from agent.dependencies import create_default_memory_store
from memory.base import MemoryStore
from agent.service import ChatService
from config import ModelProviderSettings
from llm.openai_compatible import OpenAICompatibleClient


@dataclass
class WorkbenchSession:
    session_id: str
    memory: MemoryStore = field(default_factory=create_default_memory_store)
    service: ChatService = field(init=False)
    model_services: dict[str, ChatService] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.service = ChatService(memory=self.memory)

    def service_for_provider(self, provider: ModelProviderSettings) -> ChatService:
        key = f"{provider.name}:{provider.model_name}"
        if key not in self.model_services:
            self.model_services[key] = ChatService(
                memory=self.memory,
                model_client=OpenAICompatibleClient(provider),
            )
        return self.model_services[key]


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, WorkbenchSession] = {}

    def get_or_create(self, session_id: str | None = None) -> WorkbenchSession:
        key = session_id or uuid4().hex
        if key not in self._sessions:
            self._sessions[key] = WorkbenchSession(session_id=key)
        return self._sessions[key]

    async def close(self) -> None:
        for session in self._sessions.values():
            await session.service.runner.close()
            for service in session.model_services.values():
                await service.runner.close()
