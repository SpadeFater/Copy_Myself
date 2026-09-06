from __future__ import annotations

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.chat import create_router
from api.routes.models import create_router as create_model_router
from api.session_store import SessionStore
from config import load_settings
from app_logging import configure_logging


def create_app(session_store: SessionStore | None = None) -> FastAPI:
    settings = load_settings()
    active_store = session_store or SessionStore()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        await active_store.close()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="API for the Copy_Myself visual personal-butler workbench.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(create_router(active_store), prefix="/api")
    app.include_router(create_model_router(), prefix="/api")

    return app


app = create_app()


def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    uvicorn.run("api.app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
