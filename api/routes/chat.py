from __future__ import annotations

from dataclasses import replace

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from agent.service import ChatService
from api.schemas import ApprovalRequest, ChatRequest, ChatResponse, StatusResponse
from api.session_store import SessionStore
from config import list_model_provider_settings


def create_router(session_store: SessionStore) -> APIRouter:
    router = APIRouter()

    def service_for_request(session, model: str | None):
        if not model:
            return session.service
        clean_model = model.strip()
        if not clean_model:
            raise HTTPException(status_code=400, detail="Model name cannot be empty.")
        for provider in list_model_provider_settings():
            if clean_model in provider.available_models:
                return session.service_for_provider(replace(provider, model_name=clean_model))
        raise HTTPException(status_code=400, detail=f"Model is not in a probed provider catalog: {clean_model}")

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
        service = service_for_request(session, request.model)
        result = await service.achat(request.message, session.session_id)
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
        services = [session.service, *session.model_services.values()]
        result = None
        for service in services:
            candidate = await service.resume(approval_id, request.approved, session.session_id)
            if candidate.status != "failed" or candidate.response != "approval_session_mismatch":
                result = candidate
                break
        if result is None:
            result = ChatService._failed("approval_session_mismatch")
        if result.status == "failed":
            raise HTTPException(status_code=409, detail=result.response)
        payload = ChatResponse(message=result.message, response=result.response, intent=result.intent, tool_result=result.tool_result, memory_context=result.memory_context, session_id=session.session_id, status=result.status, pending_approval=result.pending_approval.__dict__ if result.pending_approval else None)
        return JSONResponse(status_code=202 if result.status == "pending_approval" else 200, content=payload.model_dump(mode="json"))

    return router
