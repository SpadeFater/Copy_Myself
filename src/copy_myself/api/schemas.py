from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None


class ChatResponse(BaseModel):
    message: str
    response: str
    intent: str
    tool_result: dict[str, Any] | None = None
    memory_context: list[str] = []
    session_id: str | None = None


class StatusResponse(BaseModel):
    name: str
    surface: str
    status: str
