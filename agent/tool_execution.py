from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langgraph.types import interrupt

from .mcp_client import McpGatewayClient


@dataclass(frozen=True)
class PendingApproval:
    approval_id: str
    service_id: str
    tool: str
    arguments: dict[str, Any]
    summary: str
    expires_at: str


class ToolExecutionCoordinator:
    def __init__(self, client: McpGatewayClient | None = None) -> None:
        self.client = client or McpGatewayClient()

    async def definitions(self) -> list[dict[str, Any]]:
        return await self.client.definitions()

    async def execute(self, name: str, arguments: dict[str, Any], session_id: str) -> dict[str, Any]:
        payload = await self.client.call(name, arguments, session_id)
        if payload.get("code") != "approval_required":
            return payload
        pending = PendingApproval(**{key: payload[key] for key in PendingApproval.__dataclass_fields__})
        approved = bool(interrupt(pending.__dict__))
        return await self.client.approve(pending.approval_id, approved, session_id)

    async def close(self) -> None:
        await self.client.close()
