from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from agent.service import ChatService
from api.schemas import ApprovalRequest, ChatRequest, ChatResponse, StatusResponse
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
    async def chat(request: ChatRequest):
        session = session_store.get_or_create(request.session_id)
        result = await session.service.achat(request.message, session.session_id)
        payload = ChatResponse(
            message=request.message,
            response=result.response,
            intent=result.intent,
            tool_result=result.tool_result,
            memory_context=result.memory_context,
            session_id=session.session_id,
            status=result.status,
            pending_approval=result.pending_approval.__dict__ if result.pending_approval else None,
        )
        return JSONResponse(status_code=202 if result.status == "pending_approval" else 200, content=payload.model_dump(mode="json"))

    @router.post("/approvals/{approval_id}", response_model=ChatResponse)
    async def approval(approval_id: str, request: ApprovalRequest):
        session = session_store.get_or_create(request.session_id)
        result = await session.service.resume(approval_id, request.approved, session.session_id)
        if result.status == "failed":
            raise HTTPException(status_code=409, detail=result.response)
        payload = ChatResponse(message=result.message, response=result.response, intent=result.intent, tool_result=result.tool_result, memory_context=result.memory_context, session_id=session.session_id, status=result.status, pending_approval=result.pending_approval.__dict__ if result.pending_approval else None)
        return JSONResponse(status_code=202 if result.status == "pending_approval" else 200, content=payload.model_dump(mode="json"))

    return router
