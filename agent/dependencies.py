from __future__ import annotations

import os
from pathlib import Path

from config import load_settings
from llm.base import ModelClient
from llm.openai_compatible import OpenAICompatibleClient
from memory import GraphMemoryStore
from tools import TimeTool, ToolRegistry
from tools.filesystem import FileSystemTool

MEMORY_PATH_ENV = "COPY_MYSELF_MEMORY_PATH"
FILESYSTEM_ROOTS_ENV = "COPY_MYSELF_FILESYSTEM_ROOTS"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEMORY_PATH = PROJECT_ROOT / "memoryGraphData" / "memory_graph.sqlite3"


def default_filesystem_roots() -> list[Path]:
    roots = [Path.cwd()]
    home = Path.home()
    roots.extend(home / name for name in ("Desktop", "Documents", "Downloads"))
    override = os.getenv(FILESYSTEM_ROOTS_ENV)
    if override:
        roots.extend(Path(item).expanduser() for item in override.split(os.pathsep) if item.strip())
    unique_roots: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        resolved = root.resolve()
        if resolved not in seen:
            unique_roots.append(resolved)
            seen.add(resolved)
    return unique_roots


def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(TimeTool())
    registry.register(FileSystemTool(default_filesystem_roots()))
    return registry


def build_model_client() -> ModelClient | None:
    settings = load_settings()
    for provider in settings.model.providers:
        if provider.enabled:
            return OpenAICompatibleClient(provider)
    return None


def default_memory_path() -> Path:
    override = os.getenv(MEMORY_PATH_ENV)
    if not override:
        return DEFAULT_MEMORY_PATH
    override_path = Path(override).expanduser()
    return override_path if override_path.is_absolute() else PROJECT_ROOT / override_path


def create_default_memory_store() -> GraphMemoryStore:
    return GraphMemoryStore(default_memory_path())
