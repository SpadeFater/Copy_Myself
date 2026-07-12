from copy_myself.gui.view_model import PENDING_RESPONSE, WorkbenchViewModel
from copy_myself.memory import GraphMemoryStore, PersistentMemoryStore


def test_view_model_starts_with_welcome_message() -> None:
    view_model = WorkbenchViewModel()

    assert view_model.messages[0].role == "assistant"
    assert "Copy_Myself" in view_model.messages[0].content
    assert view_model.latest_run is None


def test_send_message_updates_messages_and_run_summary() -> None:
    view_model = WorkbenchViewModel()

    run = view_model.send_message("health check")

    assert view_model.messages[-2].role == "user"
    assert view_model.messages[-2].content == "health check"
    assert view_model.messages[-1].role == "assistant"
    assert run.intent == "health_check"
    assert run.tool_result == {"status": "ok", "source": "agent"}
    assert view_model.latest_run == run


def test_begin_message_adds_pending_assistant_message() -> None:
    view_model = WorkbenchViewModel()

    clean_message = view_model.begin_message(" hello ")

    assert clean_message == "hello"
    assert view_model.messages[-2].role == "user"
    assert view_model.messages[-2].content == "hello"
    assert view_model.messages[-1].role == "assistant"
    assert view_model.messages[-1].content == PENDING_RESPONSE


def test_complete_message_replaces_pending_assistant_message() -> None:
    view_model = WorkbenchViewModel()
    clean_message = view_model.begin_message("hello")
    state = {
        "response": "real model response",
        "intent": "chat",
        "tool_result": None,
        "memory_context": [],
    }

    summary = view_model.complete_message(clean_message, state)

    assert summary.response == "real model response"
    assert view_model.messages[-1].content == "real model response"
    assert view_model.latest_run == summary


def test_send_message_ignores_blank_input() -> None:
    view_model = WorkbenchViewModel()
    before = list(view_model.messages)

    result = view_model.send_message("   ")

    assert result is None
    assert view_model.messages == before


def test_view_model_lists_complete_memory_items(tmp_path) -> None:
    memory = PersistentMemoryStore(root=tmp_path, session_id="session-a")
    view_model = WorkbenchViewModel(memory=memory)

    memory.save("user", "完整记忆给用户看")

    assert view_model.complete_memory_items() == ["user: 完整记忆给用户看"]


def test_start_new_conversation_flushes_memory_and_resets_chat(tmp_path) -> None:
    memory = PersistentMemoryStore(root=tmp_path, session_id="session-a")
    view_model = WorkbenchViewModel(memory=memory)
    view_model.begin_message("旧会话")
    memory.save("user", "旧会话")

    new_session_id = view_model.start_new_conversation("session-b")

    assert new_session_id == "session-b"
    assert (tmp_path / "full_memory.jsonl").exists()
    assert "旧会话" in (tmp_path / "full_memory.jsonl").read_text(encoding="utf-8")
    assert len(view_model.messages) == 1
    assert view_model.messages[0].role == "assistant"
    assert view_model.latest_run is None


def test_view_model_lists_graph_memory_node_summaries(tmp_path) -> None:
    memory = GraphMemoryStore(root=tmp_path, session_id="session-a")
    view_model = WorkbenchViewModel(memory=memory)

    memory.save_turn(
        "请记住 Copy_Myself 的记忆图方向。",
        "已记录记忆图方向。",
        {"source": "gui"},
    )

    assert view_model.complete_memory_items() == [
        "user: 请记住 Copy_Myself 的记忆图方向。 | assistant: 已记录记忆图方向。"
    ]
