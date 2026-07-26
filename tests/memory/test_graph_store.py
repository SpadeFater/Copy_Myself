from __future__ import annotations

import sqlite3

import pytest

from copy_myself.memory import GraphMemoryStore, MemoryEdge, extract_memory_node


def test_graph_store_initializes_schema_and_handles_empty_exchange(tmp_path) -> None:
    path = tmp_path / "memory.sqlite3"
    store = GraphMemoryStore(path)

    with sqlite3.connect(path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]
    assert {"memory_nodes", "memory_edges"} <= tables
    assert journal_mode == "wal"
    assert busy_timeout >= 5000

    node = store.save_exchange("", "", session="empty", source="test")

    assert node.user_input == ""
    assert node.assistant_response == ""
    assert node.session == "empty"
    assert node.source == "test"
    assert store.list_nodes() == [node]
    assert store.retrieve("", limit=0) == []
    assert store.retrieve("query-that-does-not-exist") == []


def test_save_exchange_uses_deterministic_extraction_and_persists_raw_buckets(
    tmp_path,
) -> None:
    store = GraphMemoryStore(tmp_path / "memory.sqlite3")
    user_input = (
        "Please answer in concise Chinese. The Copy_Myself project uses SQLite "
        "and LangGraph and must stay local-first. The task is in progress; "
        "next step is to review graph retrieval."
    )
    assistant_response = "Understood. I will review graph retrieval."

    node = store.save_exchange(
        user_input,
        assistant_response,
        session="session-1",
        source="unit-test",
    )

    assert node.preference_memory.language == "Chinese"
    assert node.project_memory.facts == ["Copy_Myself project uses SQLite and LangGraph"]
    assert node.task_memory.status == "in_progress"
    assert node.task_memory.next_actions == ["review graph retrieval"]
    assert "sqlite" in node.tags
    assert node.summary
    assert 0.0 <= node.importance <= 1.0
    assert 0.0 <= node.confidence <= 1.0
    assert store.get_node(node.id) == node


def test_graph_store_reload_preserves_nodes_and_deduplicates_edges(tmp_path) -> None:
    path = tmp_path / "memory.sqlite3"
    first_store = GraphMemoryStore(path)
    first = first_store.save_exchange(
        "The Copy_Myself project uses SQLite. The task is in progress.",
        "I will keep the project local-first.",
        session="session-1",
    )
    second = first_store.save_exchange(
        "The Copy_Myself project uses SQLite. The task is in progress.",
        "I will review the SQLite retrieval task.",
        session="session-2",
    )

    edges = first_store.list_edges()
    assert edges
    assert {edge.relation for edge in edges} >= {
        "semantic_similarity",
        "same_project",
        "same_task",
    }
    assert len({(edge.from_node, edge.to_node, edge.relation) for edge in edges}) == len(
        edges
    )

    duplicate = MemoryEdge(
        from_node=first.id,
        to_node=second.id,
        relation="same_project",
        weight=0.8,
        reason="duplicate test",
    )
    first_store.save_edge(duplicate)
    assert len(
        [
            edge
            for edge in first_store.list_edges()
            if edge.relation == "same_project"
        ]
    ) == 1

    reloaded = GraphMemoryStore(path)
    assert reloaded.get_node(first.id) == first
    assert reloaded.get_node(second.id) == second
    assert reloaded.list_edges() == first_store.list_edges()


def test_save_node_update_recomputes_edges_and_removes_stale_relations(tmp_path) -> None:
    store = GraphMemoryStore(tmp_path / "memory.sqlite3")
    first = store.save_exchange(
        "The Copy_Myself project uses SQLite.",
        "The project fact is saved.",
    )
    second = store.save_exchange(
        "The Copy_Myself project uses SQLite.",
        "The matching project fact is saved.",
    )
    assert store.list_edges(
        from_node=first.id,
        to_node=second.id,
        relation="same_project",
    )

    replacement = extract_memory_node(
        "Recipe note about pantry inventory.",
        "Use the oldest flour first.",
        node_id=second.id,
    )
    store.save_node(replacement)

    assert store.get_node(second.id) == replacement
    assert store.list_edges(from_node=first.id, to_node=second.id) == []
    assert store.list_edges(from_node=second.id, to_node=first.id) == []


def test_sequential_multi_instance_writes_derive_edges_from_latest_snapshot(
    tmp_path,
) -> None:
    path = tmp_path / "memory.sqlite3"
    first_store = GraphMemoryStore(path)
    second_store = GraphMemoryStore(path)

    first = first_store.save_exchange(
        "The Copy_Myself project uses SQLite. The task is in progress.",
        "The first instance saved the project memory.",
    )
    second = second_store.save_exchange(
        "The Copy_Myself project uses SQLite. The task is in progress.",
        "The second instance saved related memory.",
    )

    reloaded = GraphMemoryStore(path)
    assert {
        edge.relation
        for edge in reloaded.list_edges(from_node=first.id, to_node=second.id)
    } >= {"same_project", "same_task"}


def test_legacy_sqlite_schema_is_migrated_to_current_graph_schema(tmp_path) -> None:
    path = tmp_path / "memory.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE memory_nodes (
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
            );
            CREATE TABLE memory_edges (
                id TEXT PRIMARY KEY,
                from_node_id TEXT NOT NULL,
                to_node_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                weight REAL NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        connection.execute(
            """
            INSERT INTO memory_nodes (
                id, session_id, created_at, updated_at, user_input,
                assistant_response, summary, preference_memory_json,
                project_memory_json, task_memory_json, episode_memory_json,
                tags_json, project, task_id, importance, confidence,
                embedding_json, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-a",
                "session-a",
                "2026-07-25T00:00:00+00:00",
                "2026-07-25T00:00:00+00:00",
                "The project uses SQLite.",
                "Saved.",
                "legacy summary",
                "{}",
                '{"facts": ["The project uses SQLite"]}',
                "{}",
                "{}",
                '["sqlite"]',
                "Copy_Myself",
                "",
                0.7,
                0.8,
                "",
                "legacy",
            ),
        )

    store = GraphMemoryStore(path)
    node = store.get_node("legacy-a")

    assert node is not None
    assert node.session == "session-a"
    assert node.project_memory.facts == ["The project uses SQLite"]
    assert store.save_exchange("The project uses SQLite.", "Saved again.")
    assert store.list_edges()


def test_bad_node_json_error_names_node_and_column(tmp_path) -> None:
    store = GraphMemoryStore(tmp_path / "memory.sqlite3")
    node = store.save_exchange("Remember SQLite.", "Saved.")

    with sqlite3.connect(tmp_path / "memory.sqlite3") as connection:
        connection.execute(
            "UPDATE memory_nodes SET preference_memory = ? WHERE id = ?",
            ("{bad json", node.id),
        )

    with pytest.raises(ValueError, match=rf"memory node {node.id}.*preference_memory"):
        store.get_node(node.id)


def test_legacy_bucket_lists_are_loaded_as_empty_buckets(tmp_path) -> None:
    store = GraphMemoryStore(tmp_path / "memory.sqlite3")
    node = store.save_exchange("Remember SQLite.", "Saved.")

    with sqlite3.connect(tmp_path / "memory.sqlite3") as connection:
        connection.execute(
            "UPDATE memory_nodes SET preference_memory = ? WHERE id = ?",
            ("[]", node.id),
        )

    loaded = store.get_node(node.id)

    assert loaded is not None
    assert loaded.preference_memory.preferences == []
    assert loaded.preference_memory.habits == []
    assert loaded.preference_memory.language is None
    assert loaded.preference_memory.response_style == []


def test_bad_edge_data_error_names_edge_identity(tmp_path) -> None:
    store = GraphMemoryStore(tmp_path / "memory.sqlite3")
    first = store.save_exchange("The project uses SQLite.", "Saved.")
    second = store.save_exchange("The project uses SQLite.", "Saved again.")

    with sqlite3.connect(tmp_path / "memory.sqlite3") as connection:
        connection.execute(
            """
            UPDATE memory_edges
            SET weight = ?
            WHERE from_node = ? AND to_node = ? AND relation = ?
            """,
            (2.0, first.id, second.id, "same_project"),
        )

    with pytest.raises(
        ValueError,
        match=rf"memory edge {first.id}->{second.id} same_project",
    ):
        store.list_edges(from_node=first.id, to_node=second.id)


def test_retrieve_ranks_keyword_and_tag_matches_by_value(tmp_path) -> None:
    store = GraphMemoryStore(tmp_path / "memory.sqlite3")
    unrelated = store.save_exchange(
        "Discuss gardening plans for the weekend.",
        "The garden notes are saved.",
    )
    sqlite_node = store.save_exchange(
        "The project uses SQLite persistence.",
        "SQLite retrieval is ready.",
    )
    tagged = store.save_exchange(
        "Review the local-first memory implementation.",
        "The SQLite adapter is under review.",
    )

    results = store.retrieve("SQLite", limit=2, expand_relations=False)

    assert [node.id for node in results] == [sqlite_node.id, tagged.id]
    assert unrelated.id not in {node.id for node in results}
    assert store.retrieve("SQLite", limit=1, expand_relations=False) == [
        sqlite_node
    ]
    assert store.retrieve("SQLite", limit=-1) == []


def test_retrieve_can_expand_related_nodes_and_compose_compact_context(tmp_path) -> None:
    store = GraphMemoryStore(tmp_path / "memory.sqlite3")
    primary = store.save_exchange(
        "The Copy_Myself project uses SQLite. The task is in progress.",
        "I will implement SQLite retrieval.",
    )
    related = store.save_exchange(
        "The Copy_Myself project uses SQLite. The task is in progress.",
        "The next step is to review graph ranking.",
    )
    unrelated = store.save_exchange(
        "A completely unrelated cooking note.",
        "Use less salt next time.",
    )

    expanded = store.retrieve("retrieval", limit=3, expand_relations=True)
    assert expanded[0].id == primary.id
    assert related.id in {node.id for node in expanded}
    assert unrelated.id not in {node.id for node in expanded}

    context = store.compose_context("retrieval", limit=2)
    assert primary.id in context
    assert related.id in context
    assert unrelated.id not in context
    assert len(context) < len(primary.user_input + primary.assistant_response) * 4 + 200


def test_graph_store_keeps_legacy_save_search_adapter(tmp_path) -> None:
    store = GraphMemoryStore(tmp_path / "memory.sqlite3")

    store.save("user", "remember this local note")
    store.save("assistant", "the note was recorded")

    results = store.search("local note", limit=5)

    assert results == ["user: remember this local note"]
    assert len(store.list_nodes()) == 2


def test_graph_store_detects_preference_support_contradiction_and_supersession(
    tmp_path,
) -> None:
    store = GraphMemoryStore(tmp_path / "memory.sqlite3")
    previous = store.save_exchange(
        "I prefer concise answers. The project uses SQLite and the task is pending.",
        "The old decision is recorded.",
    )
    current = store.save_exchange(
        "I prefer concise answers. The project uses SQLite. The new decision "
        "must not keep the old path; replace it.",
        "I agree. The task is completed and the decision is updated.",
    )

    relations = {
        edge.relation
        for edge in store.list_edges(from_node=previous.id, to_node=current.id)
    }

    assert {
        "preference_relation",
        "support",
        "contradiction",
        "supersession",
    } <= relations
