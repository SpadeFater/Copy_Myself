from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Mapping

from memory.extraction import extract_memory_node
from memory.models import MemoryEdge, MemoryNode


_TOKEN_PATTERN = re.compile(r"[a-z0-9_]+|[\u4e00-\u9fff]", re.IGNORECASE)
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "project",
    "task",
    "the",
    "this",
    "to",
    "with",
}
_SUPPORT_TERMS = (
    "agree",
    "confirmed",
    "done",
    "implemented",
    "keep",
    "recorded",
    "review",
    "understood",
    "will",
)
_CONTRADICTION_TERMS = (
    "cannot",
    "contradict",
    "do not",
    "don't",
    "instead",
    "must not",
    "never",
    "no longer",
    "not",
)
_SUPERSESSION_TERMS = (
    "new decision",
    "replace",
    "replaced",
    "supersede",
    "superseded",
    "updated",
)
_RELATION_NOISE = {"episode", "user_assistant_exchange"}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN_PATTERN.findall(value.lower())
        if token not in _STOPWORDS
    }


def _text_from_mapping(value: Mapping[str, Any]) -> str:
    pieces: list[str] = []
    for item in value.values():
        if isinstance(item, Mapping):
            pieces.append(_text_from_mapping(item))
        elif isinstance(item, list):
            pieces.extend(str(part) for part in item)
        elif item is not None:
            pieces.append(str(item))
    return " ".join(pieces)


def _bucket_text(node: MemoryNode) -> str:
    return " ".join(
        (
            _text_from_mapping(node.preference_memory.to_dict()),
            _text_from_mapping(node.project_memory.to_dict()),
            _text_from_mapping(node.task_memory.to_dict()),
            _text_from_mapping(node.episode_memory.to_dict()),
        )
    )


def _node_text(node: MemoryNode) -> str:
    return " ".join(
        (
            node.user_input,
            node.assistant_response,
            node.summary,
            " ".join(node.tags),
            _bucket_text(node),
        )
    )


def _bucket_terms(node: MemoryNode, bucket: str) -> set[str]:
    value = getattr(node, bucket).to_dict()
    return _tokens(_text_from_mapping(value))


def _shared(left: Iterable[str], right: Iterable[str]) -> set[str]:
    return set(left) & set(right)


def _contains_signal(text: str, phrases: Iterable[str]) -> bool:
    return any(
        re.search(rf"\b{re.escape(phrase)}\b", text, flags=re.IGNORECASE)
        for phrase in phrases
    )


class GraphMemoryStore:
    """Local-first SQLite graph store for durable memory nodes and edges."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._is_file_database = self.path != ":memory:"
        if self.path != ":memory:":
            database_path = Path(self.path)
            database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, timeout=10.0)
        self._connection.row_factory = sqlite3.Row
        self._configure_connection()
        self._initialize_schema()

    def _configure_connection(self) -> None:
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        if self._is_file_database:
            self._connection.execute("PRAGMA journal_mode = WAL")

    def _initialize_schema(self) -> None:
        self._migrate_legacy_schema()
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS memory_nodes (
                id TEXT PRIMARY KEY,
                user_input TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                preference_memory TEXT NOT NULL,
                project_memory TEXT NOT NULL,
                task_memory TEXT NOT NULL,
                episode_memory TEXT NOT NULL,
                summary TEXT NOT NULL,
                tags TEXT NOT NULL,
                importance REAL NOT NULL,
                confidence REAL NOT NULL,
                created_at TEXT NOT NULL,
                session TEXT,
                source TEXT NOT NULL,
                metadata TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memory_edges (
                from_node TEXT NOT NULL,
                to_node TEXT NOT NULL,
                relation TEXT NOT NULL,
                weight REAL NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (from_node, to_node, relation),
                FOREIGN KEY (from_node) REFERENCES memory_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (to_node) REFERENCES memory_nodes(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_memory_edges_from
                ON memory_edges(from_node);
            CREATE INDEX IF NOT EXISTS idx_memory_edges_to
                ON memory_edges(to_node);
            """
        )
        self._connection.commit()

    def _migrate_legacy_schema(self) -> None:
        node_columns = self._table_columns("memory_nodes")
        if node_columns and "preference_memory_json" in node_columns:
            with self._connection:
                self._connection.execute("ALTER TABLE memory_nodes RENAME TO memory_nodes_legacy")
                self._create_current_nodes_table()
                self._connection.execute(
                    """
                    INSERT INTO memory_nodes (
                        id, user_input, assistant_response,
                        preference_memory, project_memory, task_memory, episode_memory,
                        summary, tags, importance, confidence, created_at,
                        session, source, metadata
                    )
                    SELECT
                        id, user_input, assistant_response,
                        preference_memory_json, project_memory_json,
                        task_memory_json, episode_memory_json,
                        summary, tags_json, importance, confidence, created_at,
                        session_id, source, '{}'
                    FROM memory_nodes_legacy
                    """
                )

        edge_columns = self._table_columns("memory_edges")
        if edge_columns and "from_node_id" in edge_columns:
            with self._connection:
                self._connection.execute("ALTER TABLE memory_edges RENAME TO memory_edges_legacy")
                self._create_current_edges_table()
                self._connection.execute(
                    """
                    INSERT OR IGNORE INTO memory_edges (
                        from_node, to_node, relation, weight, reason, created_at
                    )
                    SELECT
                        from_node_id, to_node_id, relation, weight, reason, created_at
                    FROM memory_edges_legacy
                    """
                )

    def _table_columns(self, table_name: str) -> set[str]:
        rows = self._connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {row["name"] for row in rows}

    def _create_current_nodes_table(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE memory_nodes (
                id TEXT PRIMARY KEY,
                user_input TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                preference_memory TEXT NOT NULL,
                project_memory TEXT NOT NULL,
                task_memory TEXT NOT NULL,
                episode_memory TEXT NOT NULL,
                summary TEXT NOT NULL,
                tags TEXT NOT NULL,
                importance REAL NOT NULL,
                confidence REAL NOT NULL,
                created_at TEXT NOT NULL,
                session TEXT,
                source TEXT NOT NULL,
                metadata TEXT NOT NULL
            )
            """
        )

    def _create_current_edges_table(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE memory_edges (
                from_node TEXT NOT NULL,
                to_node TEXT NOT NULL,
                relation TEXT NOT NULL,
                weight REAL NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (from_node, to_node, relation),
                FOREIGN KEY (from_node) REFERENCES memory_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (to_node) REFERENCES memory_nodes(id) ON DELETE CASCADE
            )
            """
        )

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> GraphMemoryStore:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def save_exchange(
        self,
        user_input: str,
        assistant_response: str,
        *,
        session: str | None = None,
        source: str = "local",
    ) -> MemoryNode:
        node = extract_memory_node(
            user_input,
            assistant_response,
            session=session,
            source=source,
        )
        return self.save_node(node)

    def save_node(self, node: MemoryNode) -> MemoryNode:
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._connection.execute(
                """
                INSERT INTO memory_nodes (
                    id, user_input, assistant_response,
                    preference_memory, project_memory, task_memory, episode_memory,
                    summary, tags, importance, confidence, created_at,
                    session, source, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    user_input = excluded.user_input,
                    assistant_response = excluded.assistant_response,
                    preference_memory = excluded.preference_memory,
                    project_memory = excluded.project_memory,
                    task_memory = excluded.task_memory,
                    episode_memory = excluded.episode_memory,
                    summary = excluded.summary,
                    tags = excluded.tags,
                    importance = excluded.importance,
                    confidence = excluded.confidence,
                    created_at = excluded.created_at,
                    session = excluded.session,
                    source = excluded.source,
                    metadata = excluded.metadata
                """,
                self._node_values(node),
            )
            self._connection.execute(
                "DELETE FROM memory_edges WHERE from_node = ? OR to_node = ?",
                (node.id, node.id),
            )
            existing_rows = self._connection.execute(
                "SELECT * FROM memory_nodes WHERE id <> ? ORDER BY rowid",
                (node.id,),
            ).fetchall()
            existing_nodes = [self._node_from_row(row) for row in existing_rows]
            for previous in existing_nodes:
                for edge in self._derive_edges(previous, node):
                    self._insert_edge(edge)
        except Exception:
            self._connection.rollback()
            raise
        else:
            self._connection.commit()
        return node

    def save_edge(self, edge: MemoryEdge) -> MemoryEdge:
        if not isinstance(edge, MemoryEdge):
            raise TypeError("edge must be a MemoryEdge")
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._insert_edge(edge)
        except Exception:
            self._connection.rollback()
            raise
        else:
            self._connection.commit()
        return edge

    def get_node(self, node_id: str) -> MemoryNode | None:
        row = self._connection.execute(
            "SELECT * FROM memory_nodes WHERE id = ?",
            (node_id,),
        ).fetchone()
        return self._node_from_row(row) if row is not None else None

    def inspect_node(self, node_id: str) -> MemoryNode | None:
        return self.get_node(node_id)

    def list_nodes(
        self,
        limit: int | None = None,
        *,
        offset: int = 0,
    ) -> list[MemoryNode]:
        if offset < 0:
            raise ValueError("offset must be non-negative")
        query = "SELECT * FROM memory_nodes ORDER BY rowid"
        parameters: list[int] = []
        if limit is not None:
            if limit < 0:
                return []
            query += " LIMIT ? OFFSET ?"
            parameters.extend((limit, offset))
        elif offset:
            query += " LIMIT -1 OFFSET ?"
            parameters.append(offset)
        rows = self._connection.execute(query, parameters).fetchall()
        return [self._node_from_row(row) for row in rows]

    def list_edges(
        self,
        *,
        from_node: str | None = None,
        to_node: str | None = None,
        relation: str | None = None,
    ) -> list[MemoryEdge]:
        clauses: list[str] = []
        parameters: list[str] = []
        if from_node is not None:
            clauses.append("from_node = ?")
            parameters.append(from_node)
        if to_node is not None:
            clauses.append("to_node = ?")
            parameters.append(to_node)
        if relation is not None:
            clauses.append("relation = ?")
            parameters.append(relation)
        query = "SELECT * FROM memory_edges"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY rowid"
        rows = self._connection.execute(query, parameters).fetchall()
        return [self._edge_from_row(row) for row in rows]

    def inspect_edges(self, **filters: str | None) -> list[MemoryEdge]:
        return self.list_edges(**filters)

    def get_edges(self, node_id: str) -> list[MemoryEdge]:
        return [
            edge
            for edge in self.list_edges()
            if edge.from_node == node_id or edge.to_node == node_id
        ]

    def retrieve(
        self,
        query: str,
        limit: int = 5,
        *,
        expand_relations: bool = True,
    ) -> list[MemoryNode]:
        if limit <= 0:
            return []
        if not isinstance(query, str):
            raise TypeError("query must be a string")

        nodes = self.list_nodes()
        query_tokens = _tokens(query)
        phrase = query.strip().lower()
        scored: list[tuple[float, int, MemoryNode]] = []
        for index, node in enumerate(nodes):
            score = self._score_node(node, phrase, query_tokens)
            if score > 0:
                scored.append((score, index, node))
        scored.sort(key=lambda item: (-item[0], -item[2].importance, item[1]))
        if not scored:
            return []

        candidates: dict[str, tuple[float, int, MemoryNode]] = {
            node.id: item for item in scored for node in (item[2],)
        }
        if expand_relations:
            seed_nodes = [item[2] for item in scored[:limit]]
            scores_by_id = {item[2].id: item[0] for item in scored}
            order_by_id = {item[2].id: item[1] for item in scored}
            for seed in seed_nodes:
                for edge in self.get_edges(seed.id):
                    related_id = (
                        edge.to_node if edge.from_node == seed.id else edge.from_node
                    )
                    related = self.get_node(related_id)
                    if related is None:
                        continue
                    related_score = scores_by_id.get(related.id, 0.0)
                    related_score += edge.weight * 0.25
                    candidates[related.id] = (
                        related_score,
                        order_by_id.get(related.id, len(nodes)),
                        related,
                    )
        ranked = sorted(
            candidates.values(),
            key=lambda item: (-item[0], -item[2].importance, item[1]),
        )
        return [item[2] for item in ranked[:limit]]

    def compose_context(
        self,
        query: str,
        limit: int = 5,
        *,
        expand_relations: bool = True,
        max_chars: int = 4000,
    ) -> str:
        if max_chars <= 0:
            return ""
        nodes = self.retrieve(
            query,
            limit=limit,
            expand_relations=expand_relations,
        )
        parts: list[str] = []
        used = 0
        for node in nodes:
            user = node.user_input.strip().replace("\n", " ")[:180]
            assistant = node.assistant_response.strip().replace("\n", " ")[:240]
            summary = node.summary.strip().replace("\n", " ")[:240]
            part = f"[{node.id}] {summary}\nU: {user}\nA: {assistant}"
            separator = "\n\n" if parts else ""
            if used + len(separator) + len(part) > max_chars:
                break
            parts.append(part)
            used += len(separator) + len(part)
        return "\n\n".join(parts)

    def retrieve_context(
        self,
        query: str,
        limit: int = 5,
        *,
        expand_relations: bool = True,
        max_chars: int = 4000,
    ) -> str:
        return self.compose_context(
            query,
            limit=limit,
            expand_relations=expand_relations,
            max_chars=max_chars,
        )

    def save(self, role: str, content: str) -> None:
        clean_role = role.strip() or "unknown"
        if not content.strip():
            return
        if clean_role.lower() == "assistant":
            self.save_exchange("", content)
        else:
            self.save_exchange(content, "")

    def search(self, query: str, limit: int = 5) -> list[str]:
        if limit <= 0:
            return []
        needle = query.strip().lower()
        matches: list[str] = []
        for node in self.list_nodes():
            user = node.user_input.lower()
            assistant = node.assistant_response.lower()
            if needle and needle not in user and needle not in assistant:
                continue
            if node.user_input:
                matches.append(f"user: {node.user_input}")
            if node.assistant_response:
                matches.append(f"assistant: {node.assistant_response}")
        return matches[-limit:]

    def _score_node(
        self,
        node: MemoryNode,
        phrase: str,
        query_tokens: set[str],
    ) -> float:
        if not query_tokens:
            return node.importance + node.confidence * 0.1
        raw_tokens = _tokens(f"{node.user_input} {node.assistant_response}")
        summary_tokens = _tokens(node.summary)
        tag_tokens = _tokens(" ".join(node.tags))
        bucket_tokens = _tokens(_bucket_text(node))
        raw_hits = len(query_tokens & raw_tokens)
        summary_hits = len(query_tokens & summary_tokens)
        tag_hits = len(query_tokens & tag_tokens)
        bucket_hits = len(query_tokens & bucket_tokens)
        score = (
            raw_hits
            + summary_hits * 3.0
            + tag_hits * 4.0
            + bucket_hits * 2.0
        )
        if phrase and phrase in _node_text(node).lower():
            score += 2.0
        if score <= 0:
            return 0.0
        score += node.importance * 0.5 + node.confidence * 0.1
        return score

    def _derive_edges(
        self,
        previous: MemoryNode,
        current: MemoryNode,
    ) -> list[MemoryEdge]:
        if previous.id == current.id:
            return []
        previous_terms = _tokens(_node_text(previous))
        current_terms = _tokens(_node_text(current))
        shared_terms = _shared(previous_terms, current_terms) - _RELATION_NOISE
        union = (previous_terms | current_terms) - _RELATION_NOISE
        semantic_weight = len(shared_terms) / len(union) if union else 0.0
        shared_tags = _shared(previous.tags, current.tags) - {"episode"}
        edges: list[MemoryEdge] = []

        if semantic_weight >= 0.08 or shared_tags:
            reason = "shared terms: " + ", ".join(sorted(shared_terms)[:8])
            edges.append(
                MemoryEdge(
                    from_node=previous.id,
                    to_node=current.id,
                    relation="semantic_similarity",
                    weight=min(1.0, max(0.1, semantic_weight * 2.0)),
                    reason=reason,
                )
            )

        project_shared = _shared(
            _bucket_terms(previous, "project_memory"),
            _bucket_terms(current, "project_memory"),
        )
        if project_shared:
            edges.append(
                MemoryEdge(
                    from_node=previous.id,
                    to_node=current.id,
                    relation="same_project",
                    weight=0.85,
                    reason="shared project terms: " + ", ".join(sorted(project_shared)[:8]),
                )
            )

        task_shared = _shared(
            _bucket_terms(previous, "task_memory"),
            _bucket_terms(current, "task_memory"),
        )
        if task_shared:
            edges.append(
                MemoryEdge(
                    from_node=previous.id,
                    to_node=current.id,
                    relation="same_task",
                    weight=0.85,
                    reason="shared task terms: " + ", ".join(sorted(task_shared)[:8]),
                )
            )

        preference_shared = _shared(
            _bucket_terms(previous, "preference_memory"),
            _bucket_terms(current, "preference_memory"),
        )
        if preference_shared:
            edges.append(
                MemoryEdge(
                    from_node=previous.id,
                    to_node=current.id,
                    relation="preference_relation",
                    weight=0.75,
                    reason="shared preference terms: "
                    + ", ".join(sorted(preference_shared)[:8]),
                )
            )

        current_text = _node_text(current).lower()
        related = bool(project_shared or task_shared or shared_terms)
        if related and _contains_signal(current_text, _SUPPORT_TERMS):
            edges.append(
                MemoryEdge(
                    from_node=previous.id,
                    to_node=current.id,
                    relation="support",
                    weight=0.65,
                    reason="current exchange contains a deterministic support signal",
                )
            )
        if related and _contains_signal(current_text, _CONTRADICTION_TERMS):
            edges.append(
                MemoryEdge(
                    from_node=previous.id,
                    to_node=current.id,
                    relation="contradiction",
                    weight=0.7,
                    reason="current exchange contains a deterministic contradiction signal",
                )
            )
        if related and _contains_signal(current_text, _SUPERSESSION_TERMS):
            edges.append(
                MemoryEdge(
                    from_node=previous.id,
                    to_node=current.id,
                    relation="supersession",
                    weight=0.8,
                    reason="current exchange contains a deterministic supersession signal",
                )
            )
        return edges

    def _insert_edge(self, edge: MemoryEdge) -> None:
        self._connection.execute(
            """
            INSERT OR IGNORE INTO memory_edges (
                from_node, to_node, relation, weight, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                edge.from_node,
                edge.to_node,
                edge.relation,
                edge.weight,
                edge.reason,
                edge.created_at,
            ),
        )

    @staticmethod
    def _node_values(node: MemoryNode) -> tuple[Any, ...]:
        return (
            node.id,
            node.user_input,
            node.assistant_response,
            _json(node.preference_memory.to_dict()),
            _json(node.project_memory.to_dict()),
            _json(node.task_memory.to_dict()),
            _json(node.episode_memory.to_dict()),
            node.summary,
            _json(node.tags),
            node.importance,
            node.confidence,
            node.created_at,
            node.session,
            node.source,
            _json(node.metadata),
        )

    @staticmethod
    def _node_from_row(row: sqlite3.Row) -> MemoryNode:
        node_id = row["id"]
        try:
            return MemoryNode.from_dict(
                {
                    "id": node_id,
                    "user_input": row["user_input"],
                    "assistant_response": row["assistant_response"],
                    "preference_memory": _load_node_bucket_json(
                        row,
                        "preference_memory",
                    ),
                    "project_memory": _load_node_bucket_json(row, "project_memory"),
                    "task_memory": _load_node_bucket_json(row, "task_memory"),
                    "episode_memory": _load_node_bucket_json(row, "episode_memory"),
                    "summary": row["summary"],
                    "tags": _load_node_json(row, "tags"),
                    "importance": row["importance"],
                    "confidence": row["confidence"],
                    "created_at": row["created_at"],
                    "session": row["session"],
                    "source": row["source"],
                    "metadata": _load_node_json(row, "metadata"),
                }
            )
        except ValueError as error:
            message = str(error)
            if message.startswith(f"memory node {node_id}"):
                raise
            raise ValueError(f"memory node {node_id} is invalid: {error}") from error
        except TypeError as error:
            raise ValueError(f"memory node {node_id} is invalid: {error}") from error

    @staticmethod
    def _edge_from_row(row: sqlite3.Row) -> MemoryEdge:
        identity = f"{row['from_node']}->{row['to_node']} {row['relation']}"
        try:
            return MemoryEdge.from_dict(
                {
                    "from_node": row["from_node"],
                    "to_node": row["to_node"],
                    "relation": row["relation"],
                    "weight": row["weight"],
                    "reason": row["reason"],
                    "created_at": row["created_at"],
                }
            )
        except (TypeError, ValueError) as error:
            raise ValueError(f"memory edge {identity} is invalid: {error}") from error


def _load_node_json(row: sqlite3.Row, column: str) -> Any:
    node_id = row["id"]
    try:
        return json.loads(row[column])
    except json.JSONDecodeError as error:
        raise ValueError(
            f"memory node {node_id} column {column} contains invalid JSON: {error}"
        ) from error


def _load_node_bucket_json(row: sqlite3.Row, column: str) -> Any:
    value = _load_node_json(row, column)
    if isinstance(value, list):
        return {}
    return value


__all__ = ["GraphMemoryStore"]
