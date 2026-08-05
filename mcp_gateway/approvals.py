from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


def arguments_hash(arguments: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(arguments, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


@dataclass
class PendingApproval:
    approval_id: str
    session_id: str
    tool: str
    arguments: dict[str, Any]
    argument_hash: str
    expires_at: datetime
    status: str = "pending"


@dataclass(frozen=True)
class ApprovalDecision:
    approved: bool
    arguments: dict[str, Any]


class ApprovalStore:
    def __init__(self, ttl: timedelta = timedelta(minutes=5)) -> None:
        self.ttl = ttl
        self._records: dict[str, PendingApproval] = {}

    def create(self, session_id: str, tool: str, arguments: dict[str, Any]) -> PendingApproval:
        item = PendingApproval(secrets.token_urlsafe(24), session_id, tool, dict(arguments), arguments_hash(arguments), datetime.now(timezone.utc) + self.ttl)
        self._records[item.approval_id] = item
        return item

    def get(self, approval_id: str) -> PendingApproval:
        item = self._records.get(approval_id)
        if item is None:
            raise ValueError("approval_already_resolved")
        return item

    def resolve(self, approval_id: str, session_id: str, tool: str, arguments: dict[str, Any], approved: bool) -> ApprovalDecision:
        item = self._records.get(approval_id)
        if item is None or item.status != "pending":
            raise ValueError("approval_already_resolved")
        if item.session_id != session_id:
            raise ValueError("approval_session_mismatch")
        if datetime.now(timezone.utc) >= item.expires_at:
            item.status = "expired"
            raise ValueError("approval_expired")
        if item.tool != tool or item.argument_hash != arguments_hash(arguments):
            raise ValueError("approval_arguments_mismatch")
        item.status = "approved" if approved else "rejected"
        return ApprovalDecision(approved, item.arguments)
