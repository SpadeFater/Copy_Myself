from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.chat import create_router
from api.session_store import SessionStore
from config import load_settings
from app_logging import configure_logging


def create_app() -> FastAPI:
    settings = load_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="API for the Copy_Myself visual personal-butler workbench.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(create_router(SessionStore()), prefix="/api")
    return app


app = create_app()


def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    uvicorn.run("api.app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
