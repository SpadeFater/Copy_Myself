from __future__ import annotations

from fastapi import APIRouter

from copy_myself.agent.graph import run_agent
from copy_myself.api.schemas import ChatRequest, ChatResponse, StatusResponse
from copy_myself.api.session_store import SessionStore


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
        state = run_agent(request.message, memory=session.memory)
        return ChatResponse(
            message=request.message,
            response=state.get("response") or "",
            intent=state["intent"],
            tool_result=state.get("tool_result"),
            memory_context=state.get("memory_context", []),
            session_id=session.session_id,
        )

    return router
