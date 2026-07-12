from __future__ import annotations

from copy_myself.memory import GraphMemoryStore


def test_graph_memory_saves_turn_node_with_structured_buckets(tmp_path) -> None:
    store = GraphMemoryStore(root=tmp_path, session_id="session-a")

    node_id = store.save_turn(
        "以后默认中文回答。Copy_Myself 的主要界面是 PyQt workbench，请继续完善记忆图任务。",
        "我会记住中文偏好，并把 PyQt workbench 和记忆图作为项目任务推进。",
        {"source": "gui"},
    )

    nodes = store.retrieve_nodes("记忆图 PyQt 中文", limit=3)

    assert node_id
    assert len(nodes) == 1
    assert nodes[0].session_id == "session-a"
    assert nodes[0].source == "gui"
    assert "默认中文" in " ".join(nodes[0].preference_memory)
    assert "PyQt workbench" in " ".join(nodes[0].project_memory)
    assert "记忆图" in " ".join(nodes[0].task_memory)
    assert nodes[0].episode_memory


def test_graph_memory_loads_nodes_from_sqlite(tmp_path) -> None:
    first_store = GraphMemoryStore(root=tmp_path, session_id="session-a")
    first_store.save_turn(
        "项目事实：Copy_Myself 使用 LangGraph 编排。",
        "已记录 LangGraph 是编排边界。",
        {"source": "cli"},
    )

    second_store = GraphMemoryStore(root=tmp_path, session_id="session-b")

    assert second_store.list_recent() == [
        "user: 项目事实：Copy_Myself 使用 LangGraph 编排。 | assistant: 已记录 LangGraph 是编排边界。"
    ]
    assert "LangGraph" in "\n".join(second_store.get_brief_context("编排边界"))


def test_graph_memory_creates_related_edges_for_similar_nodes(tmp_path) -> None:
    store = GraphMemoryStore(root=tmp_path, session_id="session-a")
    first_id = store.save_turn(
        "继续设计 Copy_Myself 的记忆图。",
        "先保存问答节点，再做检索。",
        {"source": "gui"},
    )
    second_id = store.save_turn(
        "完善 Copy_Myself 记忆图的检索排序。",
        "检索会结合关键词、重要性和关联边。",
        {"source": "gui"},
    )

    edges = store.list_edges()

    assert first_id != second_id
    assert len(edges) == 1
    assert {edges[0].from_node_id, edges[0].to_node_id} == {first_id, second_id}
    assert edges[0].relation in {"semantic_similarity", "same_project", "same_task"}
    assert edges[0].weight > 0


def test_graph_memory_composes_ranked_brief_context(tmp_path) -> None:
    store = GraphMemoryStore(root=tmp_path, session_id="session-a")
    store.save_turn(
        "用户偏好：以后回答保持中文且简洁。",
        "已记录中文和简洁偏好。",
        {"source": "gui"},
    )
    store.save_turn(
        "任务：实现 memory graph，并保持 SQLite 本地持久化。",
        "会优先做 GraphMemoryStore、检索和 LangGraph 接入。",
        {"source": "gui"},
    )

    context = store.get_brief_context("怎么继续实现 memory graph")

    joined = "\n".join(context)
    assert "长期用户偏好:" in joined
    assert "相关任务记忆:" in joined
    assert "中文" in joined
    assert "SQLite" in joined
