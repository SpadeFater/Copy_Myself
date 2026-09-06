from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from api.schemas import ModelRefreshResponse, ModelRollbackResponse
from llm.model_sync import refresh_model_provider, rollback_model_provider_settings


def _require_local_request(request: Request) -> None:
    host = request.client.host if request.client is not None else None
    if host not in {None, "127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(status_code=403, detail="Model management is restricted to local clients.")


def create_router() -> APIRouter:
    router = APIRouter()

    @router.post("/models/{provider_name}/refresh", response_model=ModelRefreshResponse)
    def refresh(provider_name: str, request: Request) -> ModelRefreshResponse:
        _require_local_request(request)
        try:
            result = refresh_model_provider(provider_name)
        except (RuntimeError, ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return ModelRefreshResponse(
            provider=result.provider.name,
            models=list(result.models),
            current_model=result.current_model,
            current_model_available=result.current_model_available,
            validation_error=result.validation_error,
        )

    @router.post("/models/rollback", response_model=ModelRollbackResponse)
    def rollback(request: Request) -> ModelRollbackResponse:
        _require_local_request(request)
        try:
            providers = rollback_model_provider_settings()
        except (RuntimeError, ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return ModelRollbackResponse(providers=[provider.to_record() for provider in providers])

    return router
