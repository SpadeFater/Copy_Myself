from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "Copy_Myself"
    log_level: str = "INFO"
    model_name: str = "placeholder-local"


def load_settings() -> Settings:
    return Settings(
        app_name=os.getenv("COPY_MYSELF_APP_NAME", "Copy_Myself"),
        log_level=os.getenv("COPY_MYSELF_LOG_LEVEL", "INFO"),
        model_name=os.getenv("COPY_MYSELF_MODEL_NAME", "placeholder-local"),
    )
