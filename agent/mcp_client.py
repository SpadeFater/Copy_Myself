from __future__ import annotations

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from typing import Any, Awaitable, Callable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class McpGatewayClient:
    """Owns the MCP transport in one task and serializes session operations."""

    def __init__(self, session: ClientSession | None = None) -> None:
        self.session = session
        self._queue: asyncio.Queue | None = None
        self._task: asyncio.Task | None = None
        self._ready: asyncio.Future | None = None

    async def start(self) -> None:
        if self.session is not None or (self._task is not None and not self._task.done()):
            return
        loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        self._ready = loop.create_future()
        self._task = loop.create_task(self._run())
        await self._ready

    async def _run(self) -> None:
        assert self._queue is not None and self._ready is not None
        try:
            async with AsyncExitStack() as stack:
                # Gateway is trusted and resolves secret references; it still passes a minimal env downstream.
                env = dict(os.environ)
                read, write = await stack.enter_async_context(stdio_client(StdioServerParameters(command=sys.executable, args=["-m", "mcp_gateway.server"], env=env)))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                self._ready.set_result(None)
                while True:
                    item = await self._queue.get()
                    if item is None:
                        break
                    operation, future = item
                    try:
                        future.set_result(await operation(session))
                    except BaseException as exc:
                        future.set_exception(exc)
        except BaseException as exc:
            if not self._ready.done():
                self._ready.set_exception(exc)
            raise

    async def _request(self, operation: Callable[[ClientSession], Awaitable[Any]]) -> Any:
        if self.session is not None:
            return await operation(self.session)
        await self.start()
        assert self._queue is not None
        future = asyncio.get_running_loop().create_future()
        await self._queue.put((operation, future))
        return await future

    async def close(self) -> None:
        if self._queue is not None and self._task is not None:
            await self._queue.put(None)
            await self._task
        self._queue = None
        self._task = None
        self._ready = None

    async def definitions(self) -> list[dict[str, Any]]:
        async def operation(session: ClientSession):
            return [{"type": "function", "function": {"name": tool.name, "description": tool.description or "", "parameters": tool.inputSchema}} for tool in (await session.list_tools()).tools]

        return await self._request(operation)

    async def call(self, name: str, arguments: dict[str, Any], session_id: str) -> dict[str, Any]:
        return await self._call(name, {**arguments, "_session_id": session_id})

    async def approve(self, approval_id: str, approved: bool, session_id: str) -> dict[str, Any]:
        return await self._call("_copy_myself_approval", {"approval_id": approval_id, "approved": approved, "_session_id": session_id})

    async def _call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        async def operation(session: ClientSession):
            result = await session.call_tool(name, arguments)
            if result.structuredContent is not None:
                return result.structuredContent
            for content in result.content:
                if hasattr(content, "text"):
                    return json.loads(content.text)
            return {"code": "tool_call_failed"}

        return await self._request(operation)
