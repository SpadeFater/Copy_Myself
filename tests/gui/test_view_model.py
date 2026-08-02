from datetime import datetime

from copy_myself.gui.view_model import WorkbenchViewModel


def test_view_model_starts_with_welcome_message(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("COPY_MYSELF_MEMORY_PATH", str(tmp_path / "memory.sqlite3"))
    view_model = WorkbenchViewModel()

    assert view_model.messages[0].role == "assistant"
    assert "Copy_Myself" in view_model.messages[0].content
    assert view_model.latest_run is None


def test_send_message_updates_messages_and_run_summary(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("COPY_MYSELF_MEMORY_PATH", str(tmp_path / "memory.sqlite3"))
    view_model = WorkbenchViewModel()

    run = view_model.send_message("现在几点了")

    assert view_model.messages[-2].role == "user"
    assert view_model.messages[-2].content == "现在几点了"
    assert view_model.messages[-1].role == "assistant"
    assert run.intent == "time_lookup"
    assert run.display_intent == "时间查询 · getTime"
    assert run.stage_label == "时间查询 · getTime"
    assert run.tool_result["status"] == "ok"
    assert run.tool_result["source"] == "agent"
    assert run.tool_result["timezone"]
    assert datetime.fromisoformat(run.tool_result["time"]).tzinfo is not None
    assert "save_memory" in run.graph_steps
    assert view_model.latest_run == run


def test_send_message_ignores_blank_input(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("COPY_MYSELF_MEMORY_PATH", str(tmp_path / "memory.sqlite3"))
    view_model = WorkbenchViewModel()
    before = list(view_model.messages)

    result = view_model.send_message("   ")

    assert result is None
    assert view_model.messages == before
