from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication, QFrame, QLabel, QPlainTextEdit, QTextEdit

from config import list_mcp_service_settings, list_model_provider_settings
from gui import main_window as gui_main_window
from gui.main_window import MESSAGE_BODY_MAX_HEIGHT, MainWindow
from gui.view_model import ChatMessage, RunSummary, WorkbenchViewModel

_APP: QApplication | None = None


@pytest.fixture(autouse=True)
def _isolated_memory_path(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("COPY_MYSELF_MEMORY_PATH", str(tmp_path / "memory.sqlite3"))


def _app() -> QApplication:
    global _APP
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    _APP = instance
    return instance


def test_main_window_uses_scoped_fluent_theme() -> None:
    _app()
    window = MainWindow()

    stylesheet = window.styleSheet()

    assert window.centralWidget().objectName() == "WorkbenchRoot"
    assert window.findChild(QLabel, "Brand") is not None
    assert window.chat_list.objectName() == "ChatList"
    assert window.execution_list.objectName() == "StageList"
    assert window.plan_list.objectName() == "PlanList"
    assert "#WorkbenchRoot" in stylesheet
    assert "qlineargradient" in stylesheet.lower()
    assert "QWidget {" not in stylesheet
    window.close()


def test_main_window_uses_minimal_chat_shell() -> None:
    _app()
    window = MainWindow()

    assert window.findChild(QLabel, "Brand").text() == "Copy_Myself"
    assert set(window.nav_buttons) == {"记忆", "设置"}
    assert window.findChild(QFrame, "Sidebar") is None
    assert window.findChild(QFrame, "Inspector") is None
    assert window.findChild(QFrame, "HeaderBand") is None
    assert window.findChild(QFrame, "StageBand") is None
    assert not window.tool_buttons
    assert window.send_button.text() == ""
    assert "border: none" in window.styleSheet()
    assert "#ChatList" in window.styleSheet()
    window.close()


def test_toolbar_and_inspector_keep_tool_entry_without_tool_result() -> None:
    _app()
    window = MainWindow()

    assert not window.tool_buttons
    assert window.execution_list.count() > 0
    assert window.plan_list.count() > 0
    assert window.execution_graph_button.objectName() == "ExecutionGraphButton"
    assert window.execution_graph_button.parent() is not window.centralWidget()
    assert not hasattr(window, "tool_result")
    assert not window.findChildren(QTextEdit)
    window.close()


def test_chat_message_widget_wraps_long_text() -> None:
    _app()
    view_model = WorkbenchViewModel(
        messages=[
            ChatMessage(
                role="assistant",
                content="这是一段很长的管家回复，用来确认聊天区域会自动换行而不是把内容推出窗口边界。",
            )
        ]
    )
    window = MainWindow(view_model)

    item = window.chat_list.item(0)
    widget = window.chat_list.itemWidget(item)

    assert widget is not None
    assert widget.message_body.lineWrapMode() == widget.message_body.LineWrapMode.WidgetWidth
    assert item.sizeHint().height() > 30
    assert widget.message_body.height() < MESSAGE_BODY_MAX_HEIGHT
    window.close()


def test_chat_rows_use_role_aware_custom_widgets() -> None:
    _app()
    view_model = WorkbenchViewModel(
        messages=[
            ChatMessage(role="user", content="user message"),
            ChatMessage(role="assistant", content="assistant message"),
        ]
    )
    window = MainWindow(view_model)

    widgets = [
        window.chat_list.itemWidget(window.chat_list.item(index))
        for index in range(window.chat_list.count())
    ]

    assert [widget.role for widget in widgets] == ["user", "assistant"]

    from gui.widgets import ChatMessageWidget

    assert all(isinstance(widget, ChatMessageWidget) for widget in widgets)
    window.close()


def test_inspector_exposes_execution_graph_action_and_ordered_timeline() -> None:
    _app()
    window = MainWindow()

    assert window.execution_graph_button.objectName() == "ExecutionGraphButton"
    assert window.execution_graph_button.isEnabled()

    from gui.widgets import ExecutionStepWidget

    timeline_widgets = [
        window.execution_list.itemWidget(window.execution_list.item(index))
        for index in range(window.execution_list.count())
    ]
    assert all(isinstance(widget, ExecutionStepWidget) for widget in timeline_widgets)
    assert [widget.position for widget in timeline_widgets] == [1, 2, 3, 4]
    assert [widget.step_name for widget in timeline_widgets] == [
        "load_memory",
        "classify_intent",
        "run_tool",
        "create_response",
    ]
    window.close()


def test_chat_message_widget_caps_large_response_and_scrolls_inside_bubble() -> None:
    _app()
    view_model = WorkbenchViewModel(
        messages=[
            ChatMessage(
                role="assistant",
                content="\n".join(["long assistant response line"] * 80),
            )
        ]
    )
    window = MainWindow(view_model)

    item = window.chat_list.item(0)
    widget = window.chat_list.itemWidget(item)

    assert widget is not None
    assert widget.message_body.height() == MESSAGE_BODY_MAX_HEIGHT
    assert widget.message_body.verticalScrollBar().maximum() > 0
    assert item.sizeHint().height() <= MESSAGE_BODY_MAX_HEIGHT + 32
    window.close()


def test_chat_message_widget_keeps_short_response_compact_without_scrollbar() -> None:
    _app()
    view_model = WorkbenchViewModel(
        messages=[
            ChatMessage(
                role="assistant",
                content="short response",
            )
        ]
    )
    window = MainWindow(view_model)

    item = window.chat_list.item(0)
    widget = window.chat_list.itemWidget(item)

    assert widget is not None
    assert widget.height() < 120
    assert widget.message_body.verticalScrollBar().maximum() == 0
    window.close()


def test_chat_message_widget_grows_until_max_height() -> None:
    _app()
    content = "\n".join(["medium response line"] * 12)
    window = MainWindow(
        WorkbenchViewModel(
            messages=[ChatMessage(role="assistant", content=content)]
        )
    )

    widget = window.chat_list.itemWidget(window.chat_list.item(0))

    assert widget is not None
    text_height = widget.message_body.fontMetrics().lineSpacing() * 12
    assert widget.message_body.height() == text_height + 8
    assert widget.message_body.height() < MESSAGE_BODY_MAX_HEIGHT
    window.close()


def test_chat_message_body_uses_dark_integrated_style() -> None:
    _app()
    window = MainWindow(
        WorkbenchViewModel(
            messages=[ChatMessage(role="assistant", content="short response")]
        )
    )

    widget = window.chat_list.itemWidget(window.chat_list.item(0))

    assert widget is not None
    assert isinstance(widget.message_body, QPlainTextEdit)
    assert "background: transparent" in widget.message_body.styleSheet()
    assert "background: transparent" in widget.message_body.viewport().styleSheet()
    window.close()


def test_response_stream_reveals_text_before_finalizing() -> None:
    _app()
    view_model = WorkbenchViewModel()
    window = MainWindow(view_model)
    view_model.messages.append(ChatMessage(role="assistant", content=""))

    window._start_response_stream("第一段\n第二段")

    assert view_model.messages[-1].content == ""
    window._advance_response_stream()
    assert view_model.messages[-1].content == "第一"
    window._finish_response_stream()
    assert view_model.messages[-1].content == "第一段\n第二段"
    window.close()


def test_response_stream_keeps_latest_long_text_scrolled_to_bottom() -> None:
    _app()
    view_model = WorkbenchViewModel()
    window = MainWindow(view_model)
    view_model.messages.append(ChatMessage(role="assistant", content=""))
    window._start_response_stream("\n".join(["streaming response line"] * 80))

    while window._stream_timer.isActive():
        window._advance_response_stream()

    widget = window.chat_list.itemWidget(window.chat_list.item(window.chat_list.count() - 1))
    scroll_bar = widget.message_body.verticalScrollBar()

    assert scroll_bar.maximum() > 0
    assert scroll_bar.value() == scroll_bar.maximum()
    window.close()


def test_send_message_shows_thinking_before_agent_run(monkeypatch) -> None:
    _app()
    view_model = WorkbenchViewModel()
    window = MainWindow(view_model)
    calls = []
    scheduled = []

    def fake_send_message(message: str) -> RunSummary:
        calls.append(message)
        return RunSummary(
            message=message,
            response="done",
            intent="chat",
            display_intent="对话",
            stage_label="对话",
            tool_result=None,
            memory_context=[],
            graph_steps=["load_memory", "classify_intent", "run_tool", "create_response", "save_memory"],
        )

    monkeypatch.setattr(view_model, "send_message", fake_send_message)
    monkeypatch.setattr(
        gui_main_window.QTimer,
        "singleShot",
        lambda delay_ms, callback: scheduled.append((delay_ms, callback)),
    )
    window.input_box.setText("slow question")

    window._send_message()

    assert calls == []
    assert view_model.messages[-2:] == [
        ChatMessage(role="user", content="slow question"),
        ChatMessage(role="assistant", content="管家正在思考问题..."),
    ]
    assert scheduled
    assert scheduled[0][0] >= 30

    scheduled[0][1]()

    assert calls == ["slow question"]
    assert view_model.messages[-1].content == ""
    window.close()


def test_time_tool_status_uses_time_labels() -> None:
    _app()
    window = MainWindow()

    window.input_box.setText("现在几点了")
    window._send_message()
    window._complete_pending_message()

    assert window.status_value.text() == "时间查询 · getTime"
    assert window.intent_value.text() == "时间查询 · getTime"
    assert "health_check" not in window.status_value.text()
    assert "health_check" not in window.intent_value.text()
    window.close()


def test_inspector_omits_footer_memory_and_settings_buttons() -> None:
    _app()
    window = MainWindow()

    assert not hasattr(window, "memory_button")
    assert not hasattr(window, "settings_button")
    assert window.findChild(QLabel, "FooterBar") is None
    window.close()


def test_nav_buttons_open_memory_dialog_and_settings_dialog() -> None:
    app = _app()
    view_model = WorkbenchViewModel()
    view_model.send_message("remember this preference")
    window = MainWindow(view_model)

    window.nav_buttons["记忆"].click()
    app.processEvents()
    assert window.memory_dialog is not None
    assert window.memory_dialog.isVisible()
    context_items = [
        window.memory_dialog.context_list.item(index).text()
        for index in range(window.memory_dialog.context_list.count())
    ]
    assert any("remember this preference" in item for item in context_items)

    window.nav_buttons["设置"].click()
    app.processEvents()
    assert window.settings_dialog is not None
    assert window.settings_dialog.isVisible()
    window.settings_dialog.close()
    window.memory_dialog.close()
    window.close()


def test_memory_dialog_shows_long_memory_in_scrollable_detail() -> None:
    app = _app()
    view_model = WorkbenchViewModel()
    long_response = "长记忆正文\n" + "\n".join(
        f"第 {index} 行：这是一段需要完整阅读的长期记忆内容。"
        for index in range(80)
    )
    view_model.memory.save_exchange("长文本记忆问题", long_response)
    window = MainWindow(view_model)

    window.nav_buttons["记忆"].click()
    app.processEvents()

    assert window.memory_dialog is not None
    dialog = window.memory_dialog
    assert isinstance(dialog.memory_detail, QPlainTextEdit)
    assert dialog.memory_detail.isReadOnly()
    assert dialog.memory_detail.lineWrapMode() == QPlainTextEdit.LineWrapMode.WidgetWidth
    assert dialog.context_list.count() == 1
    assert len(dialog.context_list.item(0).text()) < len(long_response)
    assert "第 79 行" in dialog.memory_detail.toPlainText()
    assert dialog.memory_detail.verticalScrollBar().maximum() > 0

    dialog.close()
    window.close()


def test_settings_dialog_imports_model_and_mcp_service(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("COPY_MYSELF_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("COPY_MYSELF_ACTIVE_MODEL", raising=False)
    monkeypatch.delenv("COPY_MYSELF_CURRENT_MODEL", raising=False)
    monkeypatch.delenv("COPY_MYSELF_MODEL", raising=False)
    monkeypatch.delenv("COPY_MYSELF_MODEL_NAME", raising=False)

    app = _app()
    window = MainWindow()
    window._open_settings_dialog()
    app.processEvents()
    dialog = window.settings_dialog
    assert dialog is not None
    assert dialog.tabs.count() == 2
    assert dialog.size().height() <= 600

    dialog.model_name_input.setText("Local Qwen")
    dialog.model_url_input.setText("http://127.0.0.1:11434/v1")
    dialog.model_id_input.setText("qwen2.5:7b")
    dialog.model_api_key_input.setText("local-key")
    dialog._import_model()

    providers = list_model_provider_settings()
    assert len(providers) == 1
    assert providers[0].name == "Local Qwen"
    assert providers[0].base_url == "http://127.0.0.1:11434/v1"
    assert providers[0].model_name == "qwen2.5:7b"
    assert "qwen2.5:7b" in dialog.current_model_value.text()
    assert dialog.model_providers.count() == 1

    dialog.mcp_name_input.setText("Example MCP")
    dialog.mcp_url_input.setText("https://mcp.example.com")
    dialog.mcp_transport_input.setCurrentText("http")
    dialog.mcp_command_input.setText("npx")
    dialog.mcp_args_input.setText("--yes mcp-server")
    dialog._import_mcp_service()

    services = list_mcp_service_settings()
    assert len(services) == 1
    assert services[0].name == "Example MCP"
    assert services[0].endpoint == "https://mcp.example.com"
    assert services[0].transport == "http"
    assert services[0].command == "npx"
    assert services[0].args == ("--yes", "mcp-server")
    assert dialog.mcp_services.count() == 1
    dialog.close()
    window.close()
