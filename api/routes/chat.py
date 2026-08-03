from __future__ import annotations

from fastapi import APIRouter

from agent.service import ChatService
from api.schemas import ChatRequest, ChatResponse, StatusResponse
from api.session_store import SessionStore


def create_router(session_store: SessionStore) -> APIRouter:
    router = APIRouter()

    @router.get("/status", response_model=StatusResponse)
    def status() -> StatusResponse:
        return StatusResponse(
            name="Copy_Myself",
            surface="personal-butler-workbench",
            status="ok",
        )

    @router.post("/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        session = session_store.get_or_create(request.session_id)
        result = ChatService(memory=session.memory).chat(request.message)
        return ChatResponse(
            message=request.message,
            response=result.response,
            intent=result.intent,
            tool_result=result.tool_result,
            memory_context=result.memory_context,
            session_id=session.session_id,
        )

    return router
