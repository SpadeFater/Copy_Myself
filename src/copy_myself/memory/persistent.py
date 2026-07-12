from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from copy_myself.memory.base import MemoryRecord


def default_memory_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists():
            return parent / "memory"
    return Path("memory")


@dataclass
class PersistentMemoryStore:
    """Display-only complete memory from the retired JSONL memory mechanism."""

    root: Path | str = field(default_factory=default_memory_root)
    session_id: str | None = None
    _records: list[MemoryRecord] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.session_id = self.session_id or uuid4().hex
        self._load()

    @property
    def full_memory_path(self) -> Path:
        return self.root / "full_memory.jsonl"

    @property
    def sessions_dir(self) -> Path:
        return self.root / "sessions"

    def save(self, role: str, content: str) -> None:
        clean_role = role.strip() or "unknown"
        clean_content = content.strip()
        if not clean_content:
            return
        self._records.append(
            MemoryRecord(
                role=clean_role,
                content=clean_content,
                created_at=datetime.now(UTC).isoformat(),
                session_id=self.session_id or "default",
            )
        )

    def search(self, query: str, limit: int = 5) -> list[str]:
        needle = query.strip().lower()
        if not needle:
            matches = self._records
        else:
            matches = [
                record
                for record in self._records
                if needle in record.content.lower() or needle in record.role.lower()
            ]
        return [record.format() for record in matches[-limit:]]

    def list_recent(self, limit: int = 20) -> list[str]:
        return [record.format() for record in self._records[-limit:]]

    def get_brief_context(self, query: str = "") -> list[str]:
        return []

    def flush(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.full_memory_path.write_text(
            "".join(self._serialize(record) + "\n" for record in self._records),
            encoding="utf-8",
        )
        for session_id, records in self._records_by_session().items():
            session_path = self.sessions_dir / f"{session_id}.jsonl"
            session_path.write_text(
                "".join(self._serialize(record) + "\n" for record in records),
                encoding="utf-8",
            )

    def start_new_session(self, session_id: str | None = None) -> str:
        self.flush()
        self.session_id = session_id or uuid4().hex
        return self.session_id

    def _load(self) -> None:
        if not self.full_memory_path.exists():
            return
        for line in self.full_memory_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            self._records.append(self._deserialize(line))

    def _records_by_session(self) -> dict[str, list[MemoryRecord]]:
        grouped: dict[str, list[MemoryRecord]] = defaultdict(list)
        for record in self._records:
            grouped[record.session_id].append(record)
        return dict(grouped)

    def _serialize(self, record: MemoryRecord) -> str:
        return json.dumps(
            {
                "role": record.role,
                "content": record.content,
                "created_at": record.created_at,
                "session_id": record.session_id,
            },
            ensure_ascii=False,
        )

    def _deserialize(self, line: str) -> MemoryRecord:
        data = json.loads(line)
        return MemoryRecord(
            role=str(data["role"]),
            content=str(data["content"]),
            created_at=str(data["created_at"]),
            session_id=str(data["session_id"]),
        )
