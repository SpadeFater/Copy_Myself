from __future__ import annotations

import re


def normalize_service_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", value.strip().lower()).strip("-_")
    if not slug:
        raise ValueError("invalid_service_id")
    return slug


def canonical_tool_name(service_id: str, tool: str) -> str:
    return f"{normalize_service_id(service_id)}/{tool.strip()}"


def model_tool_name(service_id: str, tool: str) -> str:
    safe_tool = re.sub(r"[^A-Za-z0-9_-]+", "_", tool.strip()).strip("_")
    if not safe_tool:
        raise ValueError("invalid_tool_name")
    return f"{normalize_service_id(service_id)}__{safe_tool}"


def split_model_tool_name(value: str) -> tuple[str, str]:
    service, separator, tool = value.partition("__")
    if not separator or not service or not tool:
        raise ValueError("invalid_model_tool_name")
    return normalize_service_id(service), tool
