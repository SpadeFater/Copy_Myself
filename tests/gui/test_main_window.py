from __future__ import annotations

import os
import subprocess
import sys
import time


class FakeEvent:
    def __init__(self, kind, content="", state=None):
        self.kind = kind
        self.content = content
        self.state = state


def test_main_window_send_message_updates_chat_list(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication

    from copy_myself.gui import main_window

    def fake_stream_agent(message, memory):
        yield FakeEvent("chunk", "fake ")
        yield FakeEvent("chunk", f"model response: {message}")
        yield FakeEvent(
            "done",
            state={
                "response": f"fake model response: {message}",
                "intent": "chat",
                "tool_result": None,
                "memory_context": [],
            },
        )

    monkeypatch.setattr(main_window, "stream_agent", fake_stream_agent)

    app = QApplication.instance() or QApplication([])
    window = main_window.MainWindow()
    window.input_box.setText("hello")

    window._send_message()
    deadline = time.time() + 2
    while window.view_model.latest_run is None and time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)

    assert window.view_model.latest_run is not None
    assert window.view_model.latest_run.response == "fake model response: hello"
    assert "fake model response: hello" in window.chat_list.item(window.chat_list.count() - 1).text()


def test_main_window_streams_chunks_into_pending_message(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication

    from copy_myself.gui import main_window

    def fake_stream_agent(message, memory):
        yield FakeEvent("chunk", "第一段")
        yield FakeEvent("chunk", "第二段")
        yield FakeEvent(
            "done",
            state={
                "response": "第一段第二段",
                "intent": "chat",
                "tool_result": None,
                "memory_context": [],
            },
        )

    monkeypatch.setattr(main_window, "stream_agent", fake_stream_agent)

    app = QApplication.instance() or QApplication([])
    window = main_window.MainWindow()
    window.input_box.setText("hello")

    window._send_message()
    deadline = time.time() + 2
    while window.view_model.latest_run is None and time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)

    assert window.chat_list.item(window.chat_list.count() - 1).text().endswith("第一段第二段")


def test_main_window_sizes_long_chat_items_to_show_full_content(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication

    from copy_myself.gui import main_window
    from copy_myself.gui.view_model import ChatMessage, WorkbenchViewModel

    app = QApplication.instance() or QApplication([])
    long_text = "长回复 " * 160
    view_model = WorkbenchViewModel(messages=[ChatMessage(role="assistant", content=long_text)])
    window = main_window.MainWindow(view_model=view_model)
    app.processEvents()

    item = window.chat_list.item(0)

    assert item.sizeHint().height() > 80


def test_main_window_does_not_show_brief_memory(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication, QLabel

    from copy_myself.gui import main_window

    app = QApplication.instance() or QApplication([])
    window = main_window.MainWindow()
    app.processEvents()

    label_texts = [label.text() for label in window.findChildren(QLabel)]

    assert "极简记忆" not in label_texts
    assert window.memory_context.parent() is None


def test_main_window_uses_compact_left_toolbar(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication, QLabel, QPushButton

    from copy_myself.gui import main_window

    app = QApplication.instance() or QApplication([])
    window = main_window.MainWindow()
    app.processEvents()

    label_texts = [label.text() for label in window.findChildren(QLabel)]
    sidebar = window.findChild(main_window.QFrame, "Sidebar")
    sidebar_button_texts = [button.text() for button in sidebar.findChildren(QPushButton)]

    assert "Copy_Myself" in label_texts
    assert all("C60" not in text for text in label_texts)
    assert sidebar_button_texts == ["工作台", "记忆", "设置"]
    assert window.complete_memory_button.text() == "记忆"
    assert window.complete_memory.parent() is None


def test_main_window_keeps_size_when_switching_pages(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication

    from copy_myself.gui import main_window

    app = QApplication.instance() or QApplication([])
    window = main_window.MainWindow()
    window.show()
    app.processEvents()
    initial_size = window.size()

    window.settings_button.click()
    app.processEvents()
    settings_size = window.size()
    window.workbench_button.click()
    app.processEvents()
    workbench_size = window.size()

    assert settings_size == initial_size
    assert workbench_size == initial_size


def test_main_window_right_inspector_hides_tool_result(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication, QLabel

    from copy_myself.gui import main_window

    app = QApplication.instance() or QApplication([])
    window = main_window.MainWindow()
    app.processEvents()

    label_texts = [label.text() for label in window.findChildren(QLabel)]

    assert "执行阶段" in label_texts
    assert "计划列表" in label_texts
    assert "可调用工具" in label_texts
    assert "工具结果" not in label_texts
    assert window.tool_result.parent() is None
    assert window.tools_list.count() >= 2


def test_main_window_memory_button_opens_complete_memory_dialog(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication

    from copy_myself.gui import main_window
    from copy_myself.gui.view_model import WorkbenchViewModel
    from copy_myself.memory import PersistentMemoryStore

    app = QApplication.instance() or QApplication([])
    memory = PersistentMemoryStore(root=tmp_path, session_id="session-a")
    memory.save("user", "只在点击按钮后查看")
    window = main_window.MainWindow(view_model=WorkbenchViewModel(memory=memory))
    app.processEvents()

    dialog = window._build_complete_memory_dialog()

    assert dialog.windowTitle() == "完整记忆"
    assert dialog.memory_list.count() == 1
    assert "只在点击按钮后查看" in dialog.memory_list.item(0).text()


def test_main_window_has_copy_myself_sci_fi_identity(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication, QLabel

    from copy_myself.gui import main_window

    app = QApplication.instance() or QApplication([])
    window = main_window.MainWindow()
    app.processEvents()

    assert window.windowTitle() == "Copy_Myself"
    assert window.findChild(main_window.BrandLogo, "BrandLogo") is not None
    label_texts = [label.text() for label in window.findChildren(QLabel)]
    assert any("Copy_Myself" in text for text in label_texts)
    assert all("C60" not in text for text in label_texts)


def test_main_window_uses_premium_gradient_sci_fi_blue_theme() -> None:
    from copy_myself.gui import main_window

    stylesheet = main_window.STYLESHEET

    assert "qlineargradient" in stylesheet
    assert "#020817" in stylesheet
    assert "#061b3a" in stylesheet
    assert "#0b5cff" in stylesheet
    assert "#35d7ff" in stylesheet
    assert "rgba(8, 28, 61" in stylesheet


def test_main_window_uses_brand_image_asset(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication

    from copy_myself.gui import main_window

    app = QApplication.instance() or QApplication([])
    window = main_window.MainWindow()
    app.processEvents()

    logo = window.findChild(main_window.BrandLogo, "BrandLogo")

    assert main_window.BRAND_LOGO_PATH.exists()
    assert logo is not None
    assert logo.image_label.pixmap() is not None
    assert not logo.image_label.pixmap().isNull()


def test_main_window_model_settings_form_saves_configuration(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication

    from copy_myself.gui import main_window

    saved = []

    def fake_save_model_settings(settings):
        saved.append(settings)

    monkeypatch.setattr(main_window, "save_model_settings", fake_save_model_settings)

    app = QApplication.instance() or QApplication([])
    window = main_window.MainWindow()
    window.settings_button.click()
    app.processEvents()

    window.model_input.setText("openrouter/auto")
    window.base_url_input.setText("https://openrouter.ai/api/v1")
    window.api_key_input.setText("secret")
    window._save_model_settings()

    assert saved
    assert saved[0].model_name == "openrouter/auto"
    assert saved[0].base_url == "https://openrouter.ai/api/v1"
    assert saved[0].api_key == "secret"
    assert "已保存" in window.settings_status.text()


def test_main_window_model_switch_loads_saved_model(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication

    from copy_myself.config import ModelSettings, Settings
    from copy_myself.gui import main_window

    monkeypatch.setattr(
        main_window,
        "list_model_settings",
        lambda: [
            ModelSettings("model-a", "key-a", "https://a.test/v1"),
            ModelSettings("model-b", "key-b", "https://b.test/v1"),
        ],
    )
    monkeypatch.setattr(
        main_window,
        "load_settings",
        lambda: Settings(model_name="model-a", api_key="key-a", base_url="https://a.test/v1"),
    )
    switched = []

    def fake_switch_active_model(model_name):
        switched.append(model_name)
        return ModelSettings(model_name, f"key-{model_name}", f"https://{model_name}.test/v1")

    monkeypatch.setattr(main_window, "switch_active_model", fake_switch_active_model)

    app = QApplication.instance() or QApplication([])
    window = main_window.MainWindow()
    window.model_switch_combo.setCurrentText("model-b")
    app.processEvents()

    assert switched[-1] == "model-b"
    assert window.model_input.text() == "model-b"
    assert window.api_key_input.text() == "key-model-b"
    assert window.base_url_input.text() == "https://model-b.test/v1"


def test_main_window_settings_display_active_agent_model(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication

    from copy_myself.config import ModelSettings, Settings
    from copy_myself.gui import main_window

    monkeypatch.setattr(
        main_window,
        "list_model_settings",
        lambda: [
            ModelSettings("model-a", "key-a", "https://a.test/v1"),
            ModelSettings("model-b", "key-b", "https://b.test/v1"),
        ],
    )
    monkeypatch.setattr(
        main_window,
        "load_settings",
        lambda: Settings(model_name="model-a", api_key="key-a", base_url="https://a.test/v1"),
    )

    app = QApplication.instance() or QApplication([])
    window = main_window.MainWindow()

    assert window.model_switch_combo.currentText() == "model-a"
    assert window.model_input.text() == "model-a"
    assert window.api_key_input.text() == "key-a"
    assert window.base_url_input.text() == "https://a.test/v1"


def test_main_window_imports_mcp_service_from_settings(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication

    from copy_myself.gui import main_window

    saved = []

    def fake_save_mcp_service_settings(settings):
        saved.append(settings)

    monkeypatch.setattr(main_window, "save_mcp_service_settings", fake_save_mcp_service_settings)
    monkeypatch.setattr(main_window, "list_mcp_service_settings", lambda: list(saved))

    app = QApplication.instance() or QApplication([])
    window = main_window.MainWindow()
    window.settings_button.click()
    app.processEvents()

    window.mcp_name_input.setText("filesystem")
    window.mcp_endpoint_input.setText("npx -y @modelcontextprotocol/server-filesystem .")
    window._save_mcp_service()

    tool_items = [window.tools_list.item(index).text() for index in range(window.tools_list.count())]

    assert saved[0].name == "filesystem"
    assert saved[0].endpoint == "npx -y @modelcontextprotocol/server-filesystem ."
    assert "已导入 MCP：filesystem" in window.mcp_status.text()
    assert any("MCP · filesystem" in item for item in tool_items)


def test_main_window_can_show_without_crashing() -> None:
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    command = [
        sys.executable,
        "-c",
        (
            "from PyQt6.QtWidgets import QApplication; "
            "from copy_myself.gui.main_window import MainWindow; "
            "app = QApplication([]); "
            "window = MainWindow(); "
            "window.show(); "
            "app.processEvents(); "
            "print('shown')"
        ),
    ]

    result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=5)

    assert result.returncode == 0, result.stderr
    assert "shown" in result.stdout


def test_main_window_new_conversation_flushes_and_resets(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication

    from copy_myself.gui import main_window
    from copy_myself.gui.view_model import WorkbenchViewModel
    from copy_myself.memory import PersistentMemoryStore

    app = QApplication.instance() or QApplication([])
    memory = PersistentMemoryStore(root=tmp_path, session_id="session-a")
    view_model = WorkbenchViewModel(memory=memory)
    window = main_window.MainWindow(view_model=view_model)
    memory.save("user", "需要落盘的记忆")
    view_model.begin_message("hello")

    window._start_new_conversation()
    app.processEvents()

    assert (tmp_path / "full_memory.jsonl").exists()
    assert window.chat_list.count() == 1
    assert window.view_model.latest_run is None


def test_main_window_close_event_flushes_memory(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtGui import QCloseEvent
    from PyQt6.QtWidgets import QApplication

    from copy_myself.gui import main_window
    from copy_myself.gui.view_model import WorkbenchViewModel
    from copy_myself.memory import PersistentMemoryStore

    app = QApplication.instance() or QApplication([])
    memory = PersistentMemoryStore(root=tmp_path, session_id="session-a")
    window = main_window.MainWindow(view_model=WorkbenchViewModel(memory=memory))
    memory.save("user", "关闭时保存")

    window.closeEvent(QCloseEvent())
    app.processEvents()

    assert "关闭时保存" in (tmp_path / "full_memory.jsonl").read_text(encoding="utf-8")
