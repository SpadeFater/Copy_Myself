from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

from config import load_settings
from .approvals import ApprovalStore
from .audit import AuditLog
from .catalog import ToolCatalog, descriptor
from .connections import ConnectionManager, builtin_service
from .errors import GatewayError
from .policy import ToolPolicy
from builtin_mcp.tools.generated.manager import GeneratedToolManager

APPROVAL_TOOL = "_copy_myself_approval"


class GatewayRuntime:
    def __init__(self, connections: ConnectionManager) -> None:
        self.connections = connections
        self.catalog = ToolCatalog()
        self.policy = ToolPolicy()
        self.approvals = ApprovalStore()
        self.audit = AuditLog()

    async def start(self) -> None:
        await self.connections.start()
        await self.refresh()

    async def refresh(self) -> None:
        generated = GeneratedToolManager().list_services()
        generated_ids = {item.service_id for item in generated}
        known = {item.service_id for item in self.connections.services}
        for service in generated:
            if service.service_id not in known:
                await self.connections.add_service(service)
        stale_generated: set[str] = set()
        for service_id, connection in list(self.connections.connections.items()):
            if connection.settings.metadata.get("_meta", {}).get("copy_myself", {}).get("generated") and service_id not in generated_ids:
                self.catalog.remove_service(service_id)
                stale_generated.add(service_id)
                await self.connections.remove_service(service_id)
        for service_id, connection in self.connections.connections.items():
            if service_id in stale_generated:
                continue
            if connection.status != "online":
                continue
            tools = await self.connections.list_tools(service_id)
            origin = "builtin" if service_id == "builtin" else ("generated" if connection.settings.metadata.get("_meta", {}).get("copy_myself", {}).get("generated") else "external")
            metadata = connection.settings.metadata
            self.catalog.replace_service(service_id, [descriptor(service_id, tool, origin=origin, service_metadata=metadata) for tool in tools])

    async def close(self) -> None:
        await self.connections.close()

    async def call(self, model_name: str, arguments: dict[str, Any], session_id: str) -> dict[str, Any]:
        item = self.catalog.get_by_model_name(model_name)
        if item is None:
            raise GatewayError("tool_not_found", model_name)
        metadata = dict(item.annotations)
        if item.downstream_name == "filesystem" and item.origin == "builtin":
            action = arguments.get("action")
            metadata = {"_meta": {"copy_myself": {"risk": "read_only" if action in {"list", "stat", "read", "search"} else "side_effect"}}}
        if item.downstream_name == "office" and item.origin == "builtin":
            action = arguments.get("action")
            metadata = {"_meta": {"copy_myself": {"risk": "read_only" if action in {"list_apps", "word_read_text", "excel_list_sheets", "excel_read_range", "powerpoint_list_slides", "powerpoint_read_text"} else "side_effect"}}}
        if self.policy.requires_approval(item.origin, metadata):
            pending = self.approvals.create(session_id, item.canonical_name, arguments)
            self.audit.record(session_id, item.service_id, item.canonical_name, arguments, "pending", "approval_required", approval_required=True, approval_id=pending.approval_id)
            return {"code": "approval_required", "approval_id": pending.approval_id, "service_id": item.service_id, "tool": item.canonical_name, "arguments": arguments, "summary": f"Call {item.canonical_name}", "expires_at": pending.expires_at.isoformat()}
        return await self._execute(item, arguments, session_id, "automatic")

    async def resolve(self, approval_id: str, approved: bool, session_id: str) -> dict[str, Any]:
        pending = self.approvals.get(approval_id)
        decision = self.approvals.resolve(approval_id, session_id, pending.tool, pending.arguments, approved)
        if not decision.approved:
            item = next((tool for tool in self.catalog.items() if tool.canonical_name == pending.tool), None)
            if item is not None:
                self.audit.record(session_id, item.service_id, item.canonical_name, pending.arguments, "rejected", "rejected", approval_required=True, approval_id=approval_id)
            return {"code": "user_rejected", "approval_id": approval_id}
        item = next((tool for tool in self.catalog.items() if tool.canonical_name == pending.tool), None)
        if item is None:
            raise GatewayError("tool_not_found", pending.tool)
        return await self._execute(item, decision.arguments, session_id, "approved")

    async def _execute(self, item, arguments: dict[str, Any], session_id: str, decision: str) -> dict[str, Any]:
        try:
            result = await self.connections.call_tool(item.service_id, item.downstream_name, arguments)
            payload = result.structuredContent
            if payload is None:
                payload = {"content": [getattr(part, "text", str(part)) for part in result.content]}
            outcome = "error" if result.isError else "ok"
            if outcome == "ok" and item.service_id == "builtin" and item.downstream_name == "create_tool":
                await self.refresh()
            self.audit.record(session_id, item.service_id, item.canonical_name, arguments, outcome, decision)
            return {"code": outcome, "result": payload}
        except TimeoutError as exc:
            self.audit.record(session_id, item.service_id, item.canonical_name, arguments, "error", decision, error_code="tool_timeout")
            raise GatewayError("tool_timeout", str(exc)) from exc
        except Exception as exc:
            self.audit.record(session_id, item.service_id, item.canonical_name, arguments, "error", decision, error_code="tool_call_failed")
            raise GatewayError("tool_call_failed", str(exc)) from exc


def create_server(runtime: GatewayRuntime) -> Server:
    server = Server("copy-myself-mcp-gateway")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [Tool(name=item.model_name, description=item.description, inputSchema=item.input_schema) for item in runtime.catalog.items()]

    @server.call_tool(validate_input=True)
    async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
        try:
            session_id = str(arguments.pop("_session_id", "default"))
            if name == APPROVAL_TOOL:
                payload = await runtime.resolve(str(arguments["approval_id"]), bool(arguments["approved"]), session_id)
            else:
                payload = await runtime.call(name, arguments, session_id)
            is_error = False
        except GatewayError as exc:
            payload = {"code": exc.code, "message": exc.message}
            is_error = True
        except ValueError as exc:
            payload = {"code": str(exc)}
            is_error = True
        return CallToolResult(content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))], structuredContent=payload, isError=is_error)

    return server


async def run_gateway() -> None:
    settings = load_settings()
    manager = ConnectionManager((builtin_service(), *settings.mcp_services))
    runtime = GatewayRuntime(manager)
    await runtime.start()
    try:
        server = create_server(runtime)
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    finally:
        await runtime.close()


def main() -> None:
    import anyio

    anyio.run(run_gateway)


if __name__ == "__main__":
    main()
