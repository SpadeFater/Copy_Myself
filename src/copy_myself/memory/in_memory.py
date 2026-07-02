from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InMemoryStore:
    _records: list[tuple[str, str]] = field(default_factory=list)

    def save(self, role: str, content: str) -> None:
        clean_role = role.strip() or "unknown"
        clean_content = content.strip()
        if clean_content:
            self._records.append((clean_role, clean_content))

    def search(self, query: str, limit: int = 5) -> list[str]:
        needle = query.strip().lower()
        if not needle:
            matches = self._records
        else:
            matches = [
                record
                for record in self._records
                if needle in record[1].lower() or needle in record[0].lower()
            ]
        return [f"{role}: {content}" for role, content in matches[-limit:]]
