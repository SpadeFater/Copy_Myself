from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .approvals import arguments_hash


@dataclass(frozen=True)
class AuditRecord:
    request_id: str
    session_id: str
    service_id: str
    canonical_tool: str
    argument_hash: str
    argument_summary: str
    decision: str
    started_at: str
    outcome: str
    approval_required: bool = False
    approval_id: str | None = None
    duration_ms: int = 0
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class AuditLog:
    def __init__(self) -> None:
        self.records: list[AuditRecord] = []

    def record(self, session_id: str, service_id: str, tool: str, arguments: dict[str, Any], outcome: str, decision: str = "allowed", *, approval_required: bool = False, approval_id: str | None = None, duration_ms: int = 0, error_code: str | None = None) -> AuditRecord:
        safe = {key: ("<redacted>" if any(word in key.lower() for word in ("token", "secret", "password", "authorization", "api_key")) else value) for key, value in arguments.items()}
        item = AuditRecord(secrets.token_hex(12), session_id, service_id, tool, arguments_hash(arguments), json.dumps(safe, ensure_ascii=False, default=str), decision, datetime.now(timezone.utc).isoformat(), outcome, approval_required, approval_id, duration_ms, error_code)
        self.records.append(item)
        return item
