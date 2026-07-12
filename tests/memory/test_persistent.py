from __future__ import annotations

import json

from copy_myself.memory import PersistentMemoryStore


def test_persistent_memory_flushes_full_and_session_files_for_display(tmp_path) -> None:
    store = PersistentMemoryStore(root=tmp_path, session_id="session-a")

    store.save("user", "需要展示给用户的完整记忆")
    store.save("assistant", "旧机制只保留完整记录")
    store.flush()

    full_records = [
        json.loads(line)
        for line in (tmp_path / "full_memory.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    session_records = [
        json.loads(line)
        for line in (tmp_path / "sessions" / "session-a.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert [record["role"] for record in full_records] == ["user", "assistant"]
    assert full_records == session_records
    assert store.list_recent() == [
        "user: 需要展示给用户的完整记忆",
        "assistant: 旧机制只保留完整记录",
    ]


def test_persistent_memory_does_not_provide_model_context_or_brief_file(tmp_path) -> None:
    store = PersistentMemoryStore(root=tmp_path, session_id="session-a")
    store.save("user", "这条旧完整记忆不能进入模型上下文")

    store.flush()

    assert store.get_brief_context("任意查询") == []
    assert not (tmp_path / "brief_memory.md").exists()


def test_persistent_memory_loads_existing_full_memory_for_display_only(tmp_path) -> None:
    (tmp_path / "full_memory.jsonl").write_text(
        json.dumps(
            {
                "role": "user",
                "content": "历史完整记忆会被加载",
                "created_at": "2026-07-05T10:00:00+00:00",
                "session_id": "old-session",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "brief_memory.md").write_text("- 旧摘要应被忽略\n", encoding="utf-8")

    store = PersistentMemoryStore(root=tmp_path)

    assert store.search("历史完整记忆") == ["user: 历史完整记忆会被加载"]
    assert store.get_brief_context("历史完整记忆") == []


def test_persistent_memory_start_new_session_flushes_and_rotates_session(tmp_path) -> None:
    store = PersistentMemoryStore(root=tmp_path, session_id="session-a")
    store.save("user", "第一轮")

    new_session_id = store.start_new_session("session-b")
    store.save("user", "第二轮")
    store.flush()

    assert new_session_id == "session-b"
    assert (tmp_path / "sessions" / "session-a.jsonl").exists()
    assert (tmp_path / "sessions" / "session-b.jsonl").exists()
    assert "第一轮" in (tmp_path / "sessions" / "session-a.jsonl").read_text(encoding="utf-8")
    assert "第二轮" in (tmp_path / "sessions" / "session-b.jsonl").read_text(encoding="utf-8")
