from copy_myself.gui.view_model import WorkbenchViewModel


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


def test_send_message_ignores_blank_input() -> None:
    view_model = WorkbenchViewModel()
    before = list(view_model.messages)

    result = view_model.send_message("   ")

    assert result is None
    assert view_model.messages == before
