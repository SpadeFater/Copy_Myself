from __future__ import annotations

import os
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from config import McpServiceSettings
from .errors import GatewayError


@dataclass
class ServiceConnection:
    settings: McpServiceSettings
    session: ClientSession | None = None
    status: str = "offline"
    error: str | None = None


class ConnectionManager:
    def __init__(self, services: tuple[McpServiceSettings, ...]) -> None:
        self.services = services
        self.connections: dict[str, ServiceConnection] = {}
        self._stack = AsyncExitStack()

    async def start(self) -> None:
        await self._stack.__aenter__()
        for settings in self.services:
            if not settings.enabled:
                continue
            connection = ServiceConnection(settings)
            self.connections[settings.service_id] = connection
            try:
                if settings.transport == "stdio":
                    params = StdioServerParameters(command=settings.command, args=list(settings.args), env=self._stdio_env(settings))
                    read, write = await self._stack.enter_async_context(stdio_client(params))
                elif settings.transport == "streamable_http":
                    http_client = await self._stack.enter_async_context(httpx.AsyncClient(headers=self._resolved_mapping(settings.headers), timeout=settings.timeout_seconds))
                    read, write, _ = await self._stack.enter_async_context(streamable_http_client(settings.endpoint, http_client=http_client))
                else:
                    raise GatewayError("service_start_failed", f"Unsupported transport: {settings.transport}")
                session = await self._stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                connection.session = session
                connection.status = "online"
            except Exception as exc:
                connection.status = "offline"
                connection.error = str(exc)

    async def close(self) -> None:
        await self._stack.aclose()

    async def list_tools(self, service_id: str) -> list[Any]:
        connection = self.connections.get(service_id)
        if connection is None or connection.session is None:
            raise GatewayError("service_offline", service_id)
        with anyio.fail_after(connection.settings.timeout_seconds):
            return list((await connection.session.list_tools()).tools)

    async def call_tool(self, service_id: str, name: str, arguments: dict[str, Any]):
        connection = self.connections.get(service_id)
        if connection is None or connection.session is None:
            raise GatewayError("service_offline", service_id)
        with anyio.fail_after(connection.settings.timeout_seconds):
            return await connection.session.call_tool(name, arguments)

    @staticmethod
    def _stdio_env(settings: McpServiceSettings) -> dict[str, str]:
        allowed = ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PYTHONPATH", "COPY_MYSELF_FILESYSTEM_ROOTS")
        env = {key: os.environ[key] for key in allowed if key in os.environ}
        env.update(ConnectionManager._resolved_mapping(settings.env))
        return env

    @staticmethod
    def _resolved_mapping(values: dict[str, str]) -> dict[str, str]:
        resolved: dict[str, str] = {}
        for key, value in values.items():
            if value.startswith("${") and value.endswith("}"):
                variable = value[2:-1]
                if variable not in os.environ:
                    raise GatewayError("service_start_failed", f"Missing environment variable: {variable}")
                resolved[key] = os.environ[variable]
            else:
                resolved[key] = value
        return resolved


def builtin_service(project_root: Path | None = None) -> McpServiceSettings:
    root = project_root or Path(__file__).resolve().parents[1]
    return McpServiceSettings(service_id="builtin", name="CopyMyself Builtin", transport="stdio", command=sys.executable, args=("-m", "builtin_mcp.server"), env={"PYTHONPATH": str(root)})
