from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None
    model: str | None = None


class ChatResponse(BaseModel):
    message: str
    response: str
    intent: str
    tool_result: dict[str, Any] | None = None
    memory_context: list[str] = []
    session_id: str | None = None
    status: str = "completed"
    pending_approval: dict[str, Any] | None = None


class ApprovalRequest(BaseModel):
    session_id: str
    approved: bool


class StatusResponse(BaseModel):
    name: str
    surface: str
    status: str


class ModelRefreshResponse(BaseModel):
    provider: str
    models: list[str]
    current_model: str
    current_model_available: bool
    validation_error: str | None = None


class ModelRollbackResponse(BaseModel):
    providers: list[dict[str, Any]]
