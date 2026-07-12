from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from copy_myself.memory.base import MemoryEdge, MemoryNode
from copy_myself.memory.persistent import default_memory_root


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _load_list(value: str) -> list[str]:
    loaded = json.loads(value or "[]")
    return [str(item) for item in loaded]


def _tokens(text: str) -> set[str]:
    lowered = text.lower()
    words = set(re.findall(r"[a-z0-9_]+", lowered))
    cjk_terms = {
        term
        for term in [
            "中文",
            "简洁",
            "偏好",
            "项目",
            "任务",
            "记忆",
            "记忆图",
            "检索",
            "排序",
            "本地",
            "持久化",
            "编排",
            "界面",
        ]
        if term in lowered
    }
    return words | cjk_terms


@dataclass
class ExtractedMemory:
    summary: str
    preference_memory: list[str]
    project_memory: list[str]
    task_memory: list[str]
    episode_memory: list[str]
    tags: list[str]
    project: str | None
    task_id: str | None
    importance: float
    confidence: float


@dataclass
class DeterministicMemoryExtractor:
    def extract(self, user_input: str, assistant_response: str) -> ExtractedMemory:
        combined = f"{user_input}\n{assistant_response}".strip()
        preference_memory = self._extract_preference(combined)
        project_memory = self._extract_project(combined)
        task_memory = self._extract_task(combined)
        episode_memory = [self._compact(f"用户问：{user_input} 助手答：{assistant_response}", 240)]
        tags = sorted(_tokens(combined))
        project = "Copy_Myself" if "copy_myself" in combined.lower() else None
        task_id = "memory-graph" if "记忆图" in combined or "memory graph" in combined.lower() else None
        importance = 0.8 if preference_memory or project_memory or task_memory else 0.5
        confidence = 0.75
        return ExtractedMemory(
            summary=self._compact(user_input, 120),
            preference_memory=preference_memory,
            project_memory=project_memory,
            task_memory=task_memory,
            episode_memory=episode_memory,
            tags=tags,
            project=project,
            task_id=task_id,
            importance=importance,
            confidence=confidence,
        )

    def _extract_preference(self, text: str) -> list[str]:
        memories: list[str] = []
        if "默认中文" in text or "中文" in text:
            memories.append("用户默认中文回答。")
        if "简洁" in text:
            memories.append("用户偏好简洁回答。")
        if "偏好" in text:
            memories.append(self._compact(text, 120))
        return self._unique(memories)

    def _extract_project(self, text: str) -> list[str]:
        memories: list[str] = []
        if "Copy_Myself" in text:
            memories.append("Copy_Myself 是当前项目。")
        if "PyQt workbench" in text or "PyQt" in text:
            memories.append("Copy_Myself 的主要界面方向是 PyQt workbench。")
        if "LangGraph" in text:
            memories.append("Copy_Myself 使用 LangGraph 作为编排边界。")
        if "SQLite" in text:
            memories.append("记忆图使用 SQLite 做本地持久化。")
        return self._unique(memories)

    def _extract_task(self, text: str) -> list[str]:
        memories: list[str] = []
        if "记忆图" in text or "memory graph" in text.lower():
            memories.append("当前任务是实现 memory graph 记忆图。")
        if "检索" in text or "排序" in text:
            memories.append("记忆图检索需要结合关键词、重要性和关联边排序。")
        if "任务" in text or "实现" in text:
            memories.append(self._compact(text, 140))
        return self._unique(memories)

    def _compact(self, text: str, limit: int) -> str:
        compacted = " ".join(text.split())
        if len(compacted) <= limit:
            return compacted
        return compacted[:limit].rstrip() + "..."

    def _unique(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result


@dataclass
class GraphMemoryStore:
    root: Path | str = field(default_factory=default_memory_root)
    session_id: str | None = None
    extractor: DeterministicMemoryExtractor = field(default_factory=DeterministicMemoryExtractor)

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.session_id = self.session_id or uuid4().hex
        self.root.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    @property
    def db_path(self) -> Path:
        return self.root / "memory_graph.sqlite3"

    def save(self, role: str, content: str) -> None:
        clean_role = role.strip() or "memory"
        clean_content = content.strip()
        if clean_content:
            self.save_turn(f"{clean_role}: {clean_content}", "", {"source": "import"})

    def save_turn(
        self,
        user_input: str,
        assistant_response: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        clean_user_input = user_input.strip()
        clean_assistant_response = assistant_response.strip()
        if not clean_user_input and not clean_assistant_response:
            return ""

        metadata = metadata or {}
        extracted = self.extractor.extract(clean_user_input, clean_assistant_response)
        node_id = uuid4().hex
        created_at = _now()
        node = MemoryNode(
            id=node_id,
            session_id=self.session_id or "default",
            created_at=created_at,
            updated_at=created_at,
            user_input=clean_user_input,
            assistant_response=clean_assistant_response,
            summary=extracted.summary,
            preference_memory=extracted.preference_memory,
            project_memory=extracted.project_memory,
            task_memory=extracted.task_memory,
            episode_memory=extracted.episode_memory,
            tags=extracted.tags,
            project=extracted.project,
            task_id=extracted.task_id,
            importance=extracted.importance,
            confidence=extracted.confidence,
            embedding=None,
            source=metadata.get("source", "agent"),
        )

        with self._connect() as connection:
            self._insert_node(connection, node)
            self._link_related_nodes(connection, node)
        return node.id

    def search(self, query: str, limit: int = 5) -> list[str]:
        return [node.format() for node in self.retrieve_nodes(query, limit=limit)]

    def retrieve_nodes(self, query: str, limit: int = 5) -> list[MemoryNode]:
        nodes = self._load_nodes()
        if not nodes:
            return []
        query_tokens = _tokens(query)
        scored = [(self._score_node(node, query_tokens), node) for node in nodes]
        scored.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
        return [node for score, node in scored if score > 0][:limit] or nodes[-limit:]

    def list_recent(self, limit: int = 20) -> list[str]:
        nodes = self._load_nodes()
        return [node.format() for node in nodes[-limit:]]

    def list_edges(self, limit: int = 20) -> list[MemoryEdge]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, from_node_id, to_node_id, relation, weight, reason, created_at
                FROM memory_edges
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            MemoryEdge(
                id=str(row["id"]),
                from_node_id=str(row["from_node_id"]),
                to_node_id=str(row["to_node_id"]),
                relation=str(row["relation"]),
                weight=float(row["weight"]),
                reason=str(row["reason"]),
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]

    def get_brief_context(self, query: str = "") -> list[str]:
        nodes = self.retrieve_nodes(query, limit=8)
        if not nodes:
            return []

        sections = [
            ("长期用户偏好:", self._collect(nodes, "preference_memory")),
            ("相关项目事实:", self._collect(nodes, "project_memory")),
            ("相关任务记忆:", self._collect(nodes, "task_memory")),
            ("相关历史过程:", self._collect(nodes, "episode_memory")),
        ]
        lines: list[str] = []
        for title, values in sections:
            if not values:
                continue
            lines.append(title)
            lines.extend(f"- {value}" for value in values[:6])
        return lines

    def flush(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def start_new_session(self, session_id: str | None = None) -> str:
        self.flush()
        self.session_id = session_id or uuid4().hex
        return self.session_id

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_nodes (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    assistant_response TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    preference_memory_json TEXT NOT NULL,
                    project_memory_json TEXT NOT NULL,
                    task_memory_json TEXT NOT NULL,
                    episode_memory_json TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    project TEXT,
                    task_id TEXT,
                    importance REAL NOT NULL,
                    confidence REAL NOT NULL,
                    embedding_json TEXT,
                    source TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_edges (
                    id TEXT PRIMARY KEY,
                    from_node_id TEXT NOT NULL,
                    to_node_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    weight REAL NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def _insert_node(self, connection: sqlite3.Connection, node: MemoryNode) -> None:
        connection.execute(
            """
            INSERT INTO memory_nodes (
                id, session_id, created_at, updated_at, user_input, assistant_response,
                summary, preference_memory_json, project_memory_json, task_memory_json,
                episode_memory_json, tags_json, project, task_id, importance, confidence,
                embedding_json, source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                node.id,
                node.session_id,
                node.created_at,
                node.updated_at,
                node.user_input,
                node.assistant_response,
                node.summary,
                _dump(node.preference_memory),
                _dump(node.project_memory),
                _dump(node.task_memory),
                _dump(node.episode_memory),
                _dump(node.tags),
                node.project,
                node.task_id,
                node.importance,
                node.confidence,
                _dump(node.embedding) if node.embedding is not None else None,
                node.source,
            ),
        )

    def _link_related_nodes(self, connection: sqlite3.Connection, node: MemoryNode) -> None:
        existing_nodes = self._load_nodes(connection)
        for existing in existing_nodes:
            if existing.id == node.id:
                continue
            relation = self._relation(existing, node)
            if relation is None:
                continue
            connection.execute(
                """
                INSERT INTO memory_edges (
                    id, from_node_id, to_node_id, relation, weight, reason, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid4().hex,
                    existing.id,
                    node.id,
                    relation[0],
                    relation[1],
                    relation[2],
                    _now(),
                ),
            )

    def _relation(self, left: MemoryNode, right: MemoryNode) -> tuple[str, float, str] | None:
        if left.task_id and left.task_id == right.task_id:
            return ("same_task", 0.9, "Nodes share the same task id.")
        if left.project and left.project == right.project:
            return ("same_project", 0.8, "Nodes share the same project.")
        overlap = set(left.tags) & set(right.tags)
        if len(overlap) >= 2:
            return ("semantic_similarity", min(0.7, 0.3 + len(overlap) * 0.1), "Nodes share tags.")
        if left.preference_memory and right.preference_memory:
            return ("preference_related", 0.6, "Nodes both contain user preference memory.")
        return None

    def _load_nodes(self, connection: sqlite3.Connection | None = None) -> list[MemoryNode]:
        close_connection = connection is None
        active_connection = connection or self._connect()
        try:
            rows = active_connection.execute(
                """
                SELECT *
                FROM memory_nodes
                ORDER BY created_at ASC
                """
            ).fetchall()
        finally:
            if close_connection:
                active_connection.close()
        return [self._row_to_node(row) for row in rows]

    def _row_to_node(self, row: sqlite3.Row) -> MemoryNode:
        embedding_json = row["embedding_json"]
        embedding = json.loads(embedding_json) if embedding_json else None
        return MemoryNode(
            id=str(row["id"]),
            session_id=str(row["session_id"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            user_input=str(row["user_input"]),
            assistant_response=str(row["assistant_response"]),
            summary=str(row["summary"]),
            preference_memory=_load_list(str(row["preference_memory_json"])),
            project_memory=_load_list(str(row["project_memory_json"])),
            task_memory=_load_list(str(row["task_memory_json"])),
            episode_memory=_load_list(str(row["episode_memory_json"])),
            tags=_load_list(str(row["tags_json"])),
            project=row["project"],
            task_id=row["task_id"],
            importance=float(row["importance"]),
            confidence=float(row["confidence"]),
            embedding=embedding,
            source=str(row["source"]),
        )

    def _score_node(self, node: MemoryNode, query_tokens: set[str]) -> float:
        if not query_tokens:
            return node.importance
        node_tokens = set(node.tags) | _tokens(node.summary)
        overlap = query_tokens & node_tokens
        text = " ".join(
            [
                node.user_input,
                node.assistant_response,
                node.summary,
                " ".join(node.preference_memory),
                " ".join(node.project_memory),
                " ".join(node.task_memory),
                " ".join(node.episode_memory),
            ]
        ).lower()
        substring_hits = sum(1 for token in query_tokens if token in text)
        relevance = len(overlap) + substring_hits
        return relevance * 1.0 + node.importance * 0.3 + node.confidence * 0.2

    def _collect(self, nodes: list[MemoryNode], field_name: str) -> list[str]:
        seen: set[str] = set()
        values: list[str] = []
        for node in nodes:
            for value in getattr(node, field_name):
                if value not in seen:
                    seen.add(value)
                    values.append(value)
        return values
